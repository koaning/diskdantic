from __future__ import annotations

import weakref
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel

from .exceptions import InconsistentFormatError, MissingPathError, UnknownFormatError
from .handlers import FileHandler, JsonHandler, MarkdownFrontmatterHandler, YamlHandler
from .utils import slugify

T = TypeVar("T", bound=BaseModel)
Predicate = Callable[[T], bool]

FORMAT_REGISTRY: Mapping[str, type[FileHandler]] = {
    "markdown": MarkdownFrontmatterHandler,
    "md": MarkdownFrontmatterHandler,
    ".md": MarkdownFrontmatterHandler,
    "json": JsonHandler,
    ".json": JsonHandler,
    "yaml": YamlHandler,
    "yml": YamlHandler,
    ".yaml": YamlHandler,
    ".yml": YamlHandler,
}

EXTENSION_REGISTRY: Mapping[str, type[FileHandler]] = {
    ".md": MarkdownFrontmatterHandler,
    ".markdown": MarkdownFrontmatterHandler,
    ".json": JsonHandler,
    ".yaml": YamlHandler,
    ".yml": YamlHandler,
}


def _resolve_handler(name: str) -> FileHandler:
    try:
        handler_cls = FORMAT_REGISTRY[name.lower()]
    except KeyError as exc:
        raise UnknownFormatError(f"Unsupported format '{name}'") from exc
    return handler_cls()


@dataclass(frozen=True)
class _SortInstruction:
    field: str
    descending: bool = False


class Collection(Generic[T]):
    """Lazy, disk-backed collection of Pydantic models.

    Parameters
    ----------
    model:
        Pydantic model type used to validate each record found on disk.
    path:
        Root directory where files live. Created automatically if missing.
    format:
        Named handler for interpreting files (``"markdown"``, ``"json"``,
        ``"yaml"``). Required when the directory is empty or mixed, otherwise
        it can be inferred from existing files.
    body_field:
        Optional field name that should receive the free-form body of a file.
        Mainly used by the markdown handler to split frontmatter from content.
    recursive:
        When ``True``, the collection scans sub-directories with ``Path.rglob``;
        otherwise only files directly inside ``path`` are considered.

    The collection loads files lazily: query methods compose filters and only
    read from disk when materialized (iteration, ``to_list``, ``first``...).
    Instances remain pure Pydantic models; disk metadata is tracked separately.
    """

    def __init__(
        self,
        model: type[T],
        path: Path | str,
        *,
        format: str | None = None,
        body_field: str | None = None,
        recursive: bool = False,
    ) -> None:
        self.model = model
        self.root = Path(path).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self._recursive = recursive
        self._handler = (
            _resolve_handler(format) if format is not None else self._infer_handler(strict=True)
        )
        self.body_field = body_field

        self._model_cache: dict[Path, T] = {}
        self._path_refs: dict[int, tuple[weakref.ReferenceType[T], Path]] = {}

    # Query entrypoints -------------------------------------------------
    def query(self) -> CollectionQuery[T]:
        return CollectionQuery(self)

    def filter(self, predicate: Predicate) -> CollectionQuery[T]:
        return self.query().filter(predicate)

    def order_by(self, field: str) -> CollectionQuery[T]:
        return self.query().order_by(field)

    def head(self, n: int = 5) -> CollectionQuery[T]:
        return self.query().head(n)

    def tail(self, n: int = 5) -> CollectionQuery[T]:
        return self.query().tail(n)

    def to_list(self) -> list[T]:
        return self.query().to_list()

    def count(self) -> int:
        return self.query().count()

    def first(self) -> T | None:
        return self.query().first()

    def last(self) -> T | None:
        return self.query().last()

    def exists(self, predicate: Predicate | None = None) -> bool:
        if predicate is None:
            return self.first() is not None
        return self.filter(predicate).first() is not None

    def __iter__(self) -> Iterator[T]:
        return iter(self.query())

    def get(self, filename: str | Path) -> T | None:
        """Load a single file by name relative to the collection root."""
        target = Path(filename)
        if not target.is_absolute():
            target = (self.root / target).resolve()
        if not target.exists() or not target.is_file():
            return None
        extensions = self._handler.extensions or (self._handler.extension,)
        if target.suffix.lower() not in extensions:
            return None
        return self._load_model(target)

    # Lifecycle operations ----------------------------------------------
    def add(self, model: T, path: Path | str | None = None) -> Path:
        # Check if model is already tracked - if so, return existing path
        existing_path = self._lookup_path(model)
        if existing_path is not None:
            return existing_path

        target = self._prepare_path(model, explicit_path=path)
        data = model.model_dump()
        self._handler.write(target, data, body_field=self.body_field)
        self._register_model(model, target)
        self._model_cache[target] = model
        return target

    def update(self, model: T) -> Path:
        path = self._lookup_path(model)
        if path is None:
            raise MissingPathError(
                "Cannot update model that was not loaded from disk. "
                "Use add() or upsert(), or provide path explicitly."
            )
        data = model.model_dump()
        self._handler.write(path, data, body_field=self.body_field)
        self._model_cache[path] = model
        return path

    def upsert(self, model: T) -> Path:
        path = self._lookup_path(model)
        if path is None:
            return self.add(model)
        return self.update(model)

    def delete(self, target: T | str | Path) -> None:
        if isinstance(target, BaseModel):
            path = self._lookup_path(target)
            if path is None:
                raise MissingPathError("Model has no associated path; cannot delete")
            self._forget_model(target)
        else:
            path = Path(target)
            if not path.is_absolute():
                path = self.root / path
        self._model_cache.pop(path, None)
        if path.exists():
            path.unlink()

    def refresh(self, model: T) -> T:
        path = self._lookup_path(model)
        if path is None:
            raise MissingPathError("Model has no associated path; cannot refresh")
        fresh = self._load_model(path, force=True)
        return fresh

    def path_for(self, model: T) -> Path | None:
        return self._lookup_path(model)

    # Internal helpers --------------------------------------------------
    def _prepare_path(self, model: T, explicit_path: Path | str | None = None) -> Path:
        if explicit_path is not None:
            path = Path(explicit_path)
            if not path.is_absolute():
                path = self.root / path
            return path
        candidate = self._derive_path_for_model(model)

        # If the derived path exists, check if it contains the same data
        if candidate.exists():
            existing_model = self._load_model(candidate, force=True)
            if existing_model.model_dump() == model.model_dump():
                # Same content - reuse this path
                return candidate

        # Path doesn't exist or contains different content - find an available name
        counter = 1
        while candidate.exists():
            candidate = candidate.with_stem(f"{candidate.stem}-{counter}")
            counter += 1
        return candidate

    def _derive_path_for_model(self, model: T) -> Path:
        data = model.model_dump()
        for key in ("slug", "id", "name", "title"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                slug = slugify(value)
                break
        else:
            slug = uuid4().hex
        filename = slug + self._handler.extension
        return self.root / filename

    def _register_model(self, model: T, path: Path) -> None:
        model_id = id(model)

        def _cleanup(_: weakref.ReferenceType[T]) -> None:
            self._path_refs.pop(model_id, None)

        ref = weakref.ref(model, _cleanup)
        self._path_refs[model_id] = (ref, path)

    def _forget_model(self, model: T) -> None:
        self._path_refs.pop(id(model), None)

    def _load_model(self, path: Path, *, force: bool = False) -> T:
        if not force and path in self._model_cache:
            return self._model_cache[path]
        data = self._handler.read(path, body_field=self.body_field)
        instance = self.model.model_validate(data)
        self._register_model(instance, path)
        self._model_cache[path] = instance
        return instance

    def _lookup_path(self, model: T) -> Path | None:
        entry = self._path_refs.get(id(model))
        if not entry:
            return None
        ref, path = entry
        if ref() is None:
            self._path_refs.pop(id(model), None)
            return None
        return path

    def _iter_paths(self) -> Iterable[Path]:
        extensions = self._handler.extensions or (self._handler.extension,)
        seen: set[Path] = set()
        for suffix in dict.fromkeys(extensions):
            pattern = f"*{suffix}"
            iterator = self.root.rglob(pattern) if self._recursive else self.root.glob(pattern)
            for path in iterator:
                if path.is_file() and path not in seen:
                    seen.add(path)
                    yield path

    def _infer_handler(self, *, strict: bool = False) -> FileHandler:
        seen_handlers: set[type[FileHandler]] = set()
        iterator = self.root.rglob("*") if self._recursive else self.root.glob("*")
        for path in iterator:
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            handler_cls = EXTENSION_REGISTRY.get(suffix)
            if handler_cls is None:
                raise UnknownFormatError(
                    f"Cannot infer handler: file '{path.name}' has unsupported "
                    f"extension '{suffix}'. Pass format=... explicitly."
                )
            seen_handlers.add(handler_cls)
            if len(seen_handlers) > 1:
                raise InconsistentFormatError(
                    "Multiple file formats detected in collection. "
                    "Pass format=... explicitly to disambiguate."
                )
        if not seen_handlers:
            if strict:
                raise UnknownFormatError(
                    "Cannot infer format for empty collection. Pass format=... explicitly."
                )
            return MarkdownFrontmatterHandler()
        handler_cls = next(iter(seen_handlers))
        return handler_cls()


class CollectionQuery(Generic[T]):
    """Lazy query pipeline over a collection."""

    def __init__(self, collection: Collection[T]) -> None:
        self._collection = collection
        self._predicates: list[Predicate] = []
        self._sort: _SortInstruction | None = None
        self._post_ops: list[Callable[[list[T]], list[T]]] = []

    # Pipeline construction ---------------------------------------------
    def filter(self, predicate: Predicate) -> CollectionQuery[T]:
        next_query = self._clone()
        next_query._predicates.append(predicate)
        return next_query

    def order_by(self, field: str) -> CollectionQuery[T]:
        descending = field.startswith("-")
        normalized = field[1:] if descending else field
        next_query = self._clone()
        next_query._sort = _SortInstruction(field=normalized, descending=descending)
        return next_query

    def head(self, n: int = 5) -> CollectionQuery[T]:
        if n < 0:
            raise ValueError("head expects a non-negative integer")
        next_query = self._clone()
        next_query._post_ops.append(lambda items, n=n: items[:n])
        return next_query

    def tail(self, n: int = 5) -> CollectionQuery[T]:
        if n < 0:
            raise ValueError("tail expects a non-negative integer")
        next_query = self._clone()
        next_query._post_ops.append(lambda items, n=n: items[-n:] if n else [])
        return next_query

    # Materialization ---------------------------------------------------
    def to_list(self) -> list[T]:
        items = [self._collection._load_model(path) for path in self._collection._iter_paths()]
        for predicate in self._predicates:
            items = [item for item in items if predicate(item)]
        if self._sort is not None:
            key = self._sort.field
            items.sort(key=lambda item, key=key: getattr(item, key), reverse=self._sort.descending)
        for operation in self._post_ops:
            items = operation(items)
        return items

    def count(self) -> int:
        return len(self.to_list())

    def first(self) -> T | None:
        for item in self:
            return item
        return None

    def last(self) -> T | None:
        items = self.to_list()
        return items[-1] if items else None

    def __iter__(self) -> Iterator[T]:
        return iter(self.to_list())

    # Utilities ---------------------------------------------------------
    def _clone(self) -> CollectionQuery[T]:
        clone = CollectionQuery(self._collection)
        clone._predicates = list(self._predicates)
        clone._sort = self._sort
        clone._post_ops = list(self._post_ops)
        return clone

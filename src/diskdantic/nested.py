from __future__ import annotations

import builtins
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

from .collection import Collection

P = TypeVar("P", bound=BaseModel)
C = TypeVar("C", bound=BaseModel)


@dataclass
class NestedRecord(Generic[P, C]):
    """Container representing a single parent folder and its child entries."""

    path: Path
    info: P
    episodes: list[C]
    episodes_collection: Collection[C]


class NestedCollection(Generic[P, C]):
    """Manage folders containing a metadata file and associated child files.

    Parameters
    ----------
    parent_model:
        Pydantic model used to validate the metadata file in each folder.
    child_model:
        Pydantic model for the child entries (episodes).
    root:
        Directory containing sub-folders, each representing a parent record.
    parent_filename:
        Name of the metadata file within each folder (e.g. ``info.yml``).
    child_pattern:
        Glob pattern used to filter child files (default ``*.md``).
    parent_format:
        File handler name for the parent metadata file (defaults to ``yaml``).
    child_format:
        Handler name for child files (defaults to ``markdown``).
    child_body_field:
        Optional field where the body content should be stored on the child model.
    """

    def __init__(
        self,
        *,
        parent_model: type[P],
        child_model: type[C],
        root: Path | str,
        parent_filename: str,
        child_pattern: str = "*.md",
        parent_format: str | None = "yaml",
        child_format: str | None = "markdown",
        child_body_field: str | None = "content",
    ) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

        self.parent_model = parent_model
        self.child_model = child_model
        self.parent_filename = parent_filename
        self.child_pattern = child_pattern
        self.parent_format = parent_format
        self.child_format = child_format
        self.child_body_field = child_body_field

    # Public API --------------------------------------------------------
    def list(self) -> builtins.list[NestedRecord[P, C]]:
        return list(self)

    def __iter__(self) -> Iterator[NestedRecord[P, C]]:
        for folder in sorted(self._iter_folders()):
            record = self._load_folder(folder)
            if record is not None:
                yield record

    def get(self, slug: str) -> NestedRecord[P, C] | None:
        folder = self.root / slug
        if not folder.is_dir():
            return None
        return self._load_folder(folder)

    def refresh(self, record: NestedRecord[P, C]) -> NestedRecord[P, C] | None:
        return self._load_folder(record.path)

    # Internal helpers --------------------------------------------------
    def _iter_folders(self) -> Iterator[Path]:
        yield from (path for path in self.root.iterdir() if path.is_dir())

    def _load_folder(self, folder: Path) -> NestedRecord[P, C] | None:
        parent_path = folder / self.parent_filename
        if not parent_path.exists():
            return None

        parent_collection = Collection(
            self.parent_model,
            path=folder,
            format=self.parent_format,
            recursive=False,
        )
        info = parent_collection.get(self.parent_filename)
        if info is None:
            return None

        episodes_collection = Collection(
            self.child_model,
            path=folder,
            format=self.child_format,
            body_field=self.child_body_field,
            recursive=False,
        )
        episodes = [
            episode
            for episode in episodes_collection.to_list()
            if self._matches_child_pattern(episodes_collection.path_for(episode))
        ]
        episodes.sort(key=lambda episode: self._sort_key(episodes_collection.path_for(episode)))
        return NestedRecord(
            path=folder,
            info=info,
            episodes=episodes,
            episodes_collection=episodes_collection,
        )

    def _matches_child_pattern(self, path: Path | None) -> bool:
        if path is None:
            return False
        return path.match(self.child_pattern)

    @staticmethod
    def _sort_key(path: Path | None) -> str:
        return path.name if path is not None else ""

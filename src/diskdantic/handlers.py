from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import orjson
import yaml


class FileHandler(ABC):
    """Abstract interface for translating between files and dictionaries."""

    extension: str
    extensions: tuple[str, ...] | None = None

    @abstractmethod
    def read(self, path: Path, *, body_field: str | None = None) -> dict[str, Any]:
        """Read the file and return a dictionary payload for Pydantic."""

    @abstractmethod
    def write(
        self,
        path: Path,
        data: Mapping[str, Any],
        *,
        body_field: str | None = None,
    ) -> None:
        """Persist a dictionary payload to disk."""


class JsonHandler(FileHandler):
    extension = ".json"
    extensions = (".json",)

    def read(self, path: Path, *, body_field: str | None = None) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def write(
        self,
        path: Path,
        data: Mapping[str, Any],
        *,
        body_field: str | None = None,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            fh.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
            fh.write(b"\n")


class YamlHandler(FileHandler):
    extension = ".yaml"
    extensions = (".yaml", ".yml")

    def read(self, path: Path, *, body_field: str | None = None) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as fh:
            payload = yaml.safe_load(fh) or {}
            if not isinstance(payload, dict):
                raise ValueError(f"YAML file {path} did not produce a mapping")
            return payload

    def write(
        self,
        path: Path,
        data: Mapping[str, Any],
        *,
        body_field: str | None = None,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(dict(data), fh, allow_unicode=True, sort_keys=False)


class MarkdownFrontmatterHandler(FileHandler):
    extension = ".md"
    extensions = (".md", ".markdown")

    def read(self, path: Path, *, body_field: str | None = None) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        meta, body = _split_frontmatter(text)
        data = dict(meta)
        field = body_field or "content"
        data[field] = body
        return data

    def write(
        self,
        path: Path,
        data: Mapping[str, Any],
        *,
        body_field: str | None = None,
    ) -> None:
        field = body_field or "content"
        payload = dict(data)
        body = payload.pop(field, "")
        frontmatter = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).strip()
        rendered = f"---\n{frontmatter}\n---\n\n{body}".rstrip() + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text

    parts = text.split("\n", 1)[1]
    if "\n---" not in parts:
        return {}, text

    frontmatter_raw, body = parts.split("\n---", 1)
    # Drop the separating newline if present
    if body.startswith("\n"):
        body = body[1:]
    meta = yaml.safe_load(frontmatter_raw) or {}
    if not isinstance(meta, dict):
        raise ValueError("Frontmatter must parse to a mapping")
    return meta, body

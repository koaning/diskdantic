"""
Disk-backed data collections powered by Pydantic models.

The public API centers around :class:`Collection`, which manages a directory
of files adhering to a shared schema described by a Pydantic ``BaseModel``.
"""

from .collection import Collection
from .handlers import JsonHandler, MarkdownFrontmatterHandler, YamlHandler
from .nested import NestedCollection, NestedRecord

__all__ = [
    "Collection",
    "NestedCollection",
    "NestedRecord",
    "MarkdownFrontmatterHandler",
    "JsonHandler",
    "YamlHandler",
]

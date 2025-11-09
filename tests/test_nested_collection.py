from __future__ import annotations

from datetime import date
from pathlib import Path
from shutil import copytree

from pydantic import BaseModel

from diskdantic import NestedCollection

FIXTURES = Path(__file__).parent / "fixtures"


def copy_fixture(name: str, destination: Path) -> Path:
    source = FIXTURES / name
    target = destination / name
    copytree(source, target)
    return target


class ShowInfo(BaseModel):
    slug: str
    title: str
    summary: str


class Episode(BaseModel):
    title: str
    date: date
    tags: list[str] = []
    content: str


def test_nested_collection_list(tmp_path: Path) -> None:
    shows_root = copy_fixture("shows", tmp_path)

    shows = NestedCollection(
        parent_model=ShowInfo,
        child_model=Episode,
        root=shows_root,
        parent_filename="info.yml",
        parent_format="yaml",
        child_format="markdown",
        child_body_field="content",
    )

    records = shows.list()
    assert [record.info.slug for record in records] == ["show1", "show2", "show3"]
    assert [len(record.episodes) for record in records] == [3, 4, 2]


def test_nested_collection_add_episode(tmp_path: Path) -> None:
    shows_root = copy_fixture("shows", tmp_path)
    shows = NestedCollection(
        parent_model=ShowInfo,
        child_model=Episode,
        root=shows_root,
        parent_filename="info.yml",
        parent_format="yaml",
        child_format="markdown",
        child_body_field="content",
    )

    show3 = shows.get("show3")
    assert show3 is not None
    assert show3.path.name == "show3"

    special = Episode(
        title="Guest Special",
        date=date(2024, 3, 5),
        tags=["special"],
        content="Extended episode",
    )
    show3.episodes_collection.add(special)
    refreshed = shows.refresh(show3)
    assert refreshed is not None
    assert len(refreshed.episodes) == 3
    assert any(ep.title == "Guest Special" for ep in refreshed.episodes)

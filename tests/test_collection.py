from __future__ import annotations

from datetime import date
from pathlib import Path
from shutil import copytree

import pytest
from pydantic import BaseModel

from diskdantic import Collection
from diskdantic.exceptions import UnknownFormatError

FIXTURES = Path(__file__).parent / "fixtures"


def copy_fixture(name: str, destination: Path) -> Path:
    source = FIXTURES / name
    target = destination / name
    copytree(source, target)
    return target


class BlogPost(BaseModel):
    title: str
    date: date
    tags: list[str] = []
    draft: bool = False
    content: str


def test_collection_basic_roundtrip(tmp_path: Path) -> None:
    blog_root = copy_fixture("blog", tmp_path)

    posts = Collection(
        BlogPost,
        path=blog_root,
        body_field="content",
        format="markdown",
    )

    all_posts = posts.order_by("date").to_list()
    assert len(all_posts) == 2
    assert all_posts[0].title == "First"

    published = posts.filter(lambda post: not post.draft).to_list()
    assert published[0].title == "First"

    first = posts.head(1).first()
    assert first is not None
    assert first.title == "First"

    last = posts.tail(1).last()
    assert last is not None
    assert last.title == "Second"

    new_post = BlogPost(
        title="Third Post",
        date=date(2024, 1, 3),
        tags=["new"],
        content="New content",
    )
    new_path = posts.add(new_post)
    assert new_path.exists()

    refreshed = posts.refresh(new_post)
    assert refreshed.title == "Third Post"

    new_post.tags.append("edited")
    posts.update(new_post)

    reloaded = posts.filter(lambda post: post.title == "Third Post").first()
    assert reloaded is not None
    assert "edited" in reloaded.tags

    posts.delete(new_post)
    assert not new_path.exists()


def test_collection_requires_format_when_empty(tmp_path: Path) -> None:
    with pytest.raises(UnknownFormatError):
        Collection(BlogPost, path=tmp_path)

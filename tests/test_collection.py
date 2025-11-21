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


def test_date_serialization_json(tmp_path: Path) -> None:
    """Test that date objects are correctly serialized in JSON format."""
    posts = Collection(BlogPost, path=tmp_path, format="json", body_field="content")

    post = BlogPost(
        title="JSON Test",
        date=date(2025, 11, 9),
        tags=["test"],
        content="Testing JSON serialization",
    )

    path = posts.add(post)

    # Verify file was created
    assert path.exists()
    assert path.suffix == ".json"

    # Verify content is valid JSON with proper date format
    import json

    with path.open("r") as f:
        data = json.load(f)
    assert data["date"] == "2025-11-09"

    # Verify we can load it back correctly
    loaded = posts.first()
    assert loaded is not None
    assert loaded.date == date(2025, 11, 9)
    assert isinstance(loaded.date, date)


def test_date_serialization_yaml(tmp_path: Path) -> None:
    """Test that date objects are correctly serialized in YAML format."""
    posts = Collection(BlogPost, path=tmp_path, format="yaml", body_field="content")

    post = BlogPost(
        title="YAML Test",
        date=date(2025, 11, 9),
        tags=["test"],
        content="Testing YAML serialization",
    )

    path = posts.add(post)

    # Verify file was created
    assert path.exists()
    assert path.suffix == ".yaml"

    # Verify content is valid YAML with proper date format
    import yaml

    with path.open("r") as f:
        data = yaml.safe_load(f)
    assert data["date"] == date(2025, 11, 9)  # YAML preserves date objects

    # Verify we can load it back correctly
    loaded = posts.first()
    assert loaded is not None
    assert loaded.date == date(2025, 11, 9)
    assert isinstance(loaded.date, date)


def test_date_serialization_markdown(tmp_path: Path) -> None:
    """Test that date objects are correctly serialized in Markdown frontmatter."""
    posts = Collection(BlogPost, path=tmp_path, format="markdown", body_field="content")

    post = BlogPost(
        title="Markdown Test",
        date=date(2025, 11, 9),
        tags=["test"],
        content="Testing Markdown serialization",
    )

    path = posts.add(post)

    # Verify file was created
    assert path.exists()
    assert path.suffix == ".md"

    # Verify content has proper frontmatter with date
    content = path.read_text()
    assert content.startswith("---")
    assert "date: 2025-11-09" in content
    assert "Testing Markdown serialization" in content

    # Verify we can load it back correctly
    loaded = posts.first()
    assert loaded is not None
    assert loaded.date == date(2025, 11, 9)
    assert isinstance(loaded.date, date)


def test_add_prevents_duplicates(tmp_path: Path) -> None:
    """Test that calling add() multiple times with same model doesn't create duplicates."""
    posts = Collection(BlogPost, path=tmp_path, format="yaml", body_field="content")

    post = BlogPost(
        title="Test Post",
        date=date(2025, 11, 9),
        tags=["test"],
        content="Testing duplicate prevention",
    )

    # Add the same model object multiple times
    path1 = posts.add(post)
    path2 = posts.add(post)
    path3 = posts.add(post)

    # All paths should be the same
    assert path1 == path2 == path3

    # Only one file should exist
    files = list(tmp_path.glob("*.yaml"))
    assert len(files) == 1
    assert files[0] == path1

    # Verify the collection only sees one post
    assert posts.count() == 1


def test_add_prevents_duplicates_from_loaded_models(tmp_path: Path) -> None:
    """Test that adding loaded models doesn't create duplicates."""
    posts = Collection(BlogPost, path=tmp_path, format="yaml", body_field="content")

    # Create and add initial posts
    initial_posts = [
        BlogPost(title="First", date=date(2025, 1, 1), content="First post"),
        BlogPost(title="Second", date=date(2025, 1, 2), content="Second post"),
        BlogPost(title="Third", date=date(2025, 1, 3), content="Third post"),
    ]

    for p in initial_posts:
        posts.add(p)

    initial_count = posts.count()
    assert initial_count == 3

    # Load posts and try to add them again (simulates iteration pattern)
    for _ in range(10):
        posts_new = Collection(BlogPost, path=tmp_path, format="yaml", body_field="content")
        for p in posts:
            posts_new.add(p)

    # Should still have exactly 3 posts and 3 files
    final_count = posts_new.count()
    files = list(tmp_path.glob("*.yaml"))

    assert final_count == 3
    assert len(files) == 3
    assert {f.stem for f in files} == {"first", "second", "third"}


def test_json_date_roundtrip_preserves_type(tmp_path: Path) -> None:
    """Test that date objects are preserved as date type after JSON roundtrip."""
    posts = Collection(BlogPost, path=tmp_path, format="json", body_field="content")

    original_date = date(2025, 11, 9)
    post = BlogPost(
        title="Date Test",
        date=original_date,
        tags=["test"],
        content="Testing date preservation",
    )

    # Write the post
    path = posts.add(post)

    # Verify JSON contains ISO 8601 string
    import json

    with path.open("r") as f:
        raw_data = json.load(f)
    assert raw_data["date"] == "2025-11-09"
    assert isinstance(raw_data["date"], str)

    # Create a NEW collection to load from disk (simulates fresh read)
    posts_reloaded = Collection(BlogPost, path=tmp_path, format="json", body_field="content")
    loaded = posts_reloaded.first()

    # Verify date type is preserved after loading in new collection
    assert loaded is not None
    assert isinstance(loaded.date, date), f"Expected date type, got {type(loaded.date)}"
    assert loaded.date == original_date
    assert loaded.date.year == 2025
    assert loaded.date.month == 11
    assert loaded.date.day == 9

# diskdantic

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/koaning/diskdantic/workflows/CI/badge.svg)](https://github.com/koaning/diskdantic/actions)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Instead of having an ORM on top of a database, why not have a collection on top of a folder?

Disk-backed collections powered by Pydantic models. Work with structured data stored as markdown, JSON, or YAML files with a simple, intuitive API.

## Features

- **Type-safe**: Built on Pydantic models for automatic validation and serialization
- **Multiple formats**: Support for markdown (with frontmatter), JSON, and YAML
- **Familiar API**: Query-like interface with `filter()`, `order_by()`, `head()`, and more
- **No database required**: Your data lives as files on disk, easily versioned with git
- **Lazy evaluation**: Efficient querying that only loads what you need
- **Simple CRUD**: Add, update, delete, and refresh models with ease

## Installation

Install from PyPI:

```bash
pip install diskdantic
```

Or install from source:

```bash
git clone https://github.com/koaning/diskdantic.git
cd diskdantic
pip install -e .
```

## Quick Start

This is pretty much the whole API:

```python
from datetime import date
from pydantic import BaseModel
from diskdantic import Collection


class BlogPost(BaseModel):
    title: str
    date: date
    tags: list[str]
    draft: bool = False
    content: str


posts = Collection(
    BlogPost,
    path="./blog/posts",
    format="markdown",    # required when the folder is empty
    body_field="content", # required when format is markdown (for the body)
)

recent = posts.filter(lambda post: not post.draft).order_by("-date").head(3)
for post in recent:
    print(post.title)

new_post = BlogPost(
    title="Hello World",
    date=date.today(),
    tags=["intro"],
    content="# Hello\n\nIt works!",
)
posts.add(new_post)
```

There are also loads of utility functions.

```python
# Get all published posts
published = posts.filter(lambda post: not post.draft)

# Get posts with specific tag
intro_posts = posts.filter(lambda post: "intro" in post.tags)

# Chain filters
recent_published = posts.filter(lambda p: not p.draft).filter(lambda p: p.date.year == 2025)

# Update an existing post
post = posts.get("hello-world.md")
post.tags.append("updated")
posts.update(post)

# Delete a post
posts.delete("old-post.md")

# Count matching items
draft_count = posts.filter(lambda p: p.draft).count()
```

## Supported Formats

diskdantic works with multiple file formats:

### Markdown (with frontmatter)
```python
posts = Collection(BlogPost, path="./posts", format="markdown", body_field="content")
```
Files are stored as markdown with YAML frontmatter, ideal for blogs and documentation.

### JSON
```python
data = Collection(MyModel, path="./data", format="json")
```
Standard JSON format for structured data.

### YAML
```python
config = Collection(ConfigModel, path="./config", format="yaml")
```
Human-readable YAML files.

## API Reference

### Query Methods

- **`filter(predicate)`** - Filter items by a predicate function
- **`order_by(field)`** - Sort by field (prefix with `-` for descending)
- **`head(n=5)`** - Get first n items
- **`tail(n=5)`** - Get last n items
- **`to_list()`** - Materialize query to list
- **`count()`** - Count matching items
- **`first()`** - Get first item or None
- **`last()`** - Get last item or None
- **`exists(predicate=None)`** - Check if any items match
- **`get(filename)`** - Load specific file by name

### Lifecycle Methods

- **`add(model, path=None)`** - Add new model to collection (returns Path)
- **`update(model)`** - Update existing model on disk (returns Path)
- **`upsert(model)`** - Add if new, update if exists (returns Path)
- **`delete(target)`** - Delete by model, filename, or Path
- **`refresh(model)`** - Reload model from disk
- **`path_for(model)`** - Get disk path for a model

### Iteration

Collections are iterable and return model instances:

```python
for post in posts:
    print(post.title)
```

## Use Cases

diskdantic is perfect for:

- **Static site generators**: Manage blog posts, documentation, or content as markdown files
- **Configuration management**: Store and query configuration files with validation
- **Data pipelines**: Process structured data files without a database
- **Git-backed CMS**: Version-controlled content management
- **Prototyping**: Quickly build apps without database setup
- **Personal knowledge bases**: Organize notes, snippets, or references

## Requirements

- Python 3.12+
- pydantic >= 2.12.4
- pyyaml >= 6.0.3
- orjson >= 3.10.0

## Why?

It makes it easier to write a custom CMS on top of your disk, which is nice. But it also feels like a fun thing that should exist. Your data stays as readable files that can be edited manually, versioned with git, and processed with standard tools—while still getting type safety and a clean API.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

Development setup:

```bash
git clone https://github.com/koaning/diskdantic.git
cd diskdantic
pip install -e ".[dev]"
pre-commit install
```

Run tests:

```bash
make test
```

## License

MIT License - see LICENSE file for details.

## Author

Created by [koaning](https://github.com/koaning) (Vincent D. Warmerdam)

## diskdantic

> Instead of having an ORM on top of a database, why not have a collection on top of a folder?

### Abstract

**diskdantic** provides disk-backed collections powered by Pydantic models, enabling you to treat a folder as a queryable database. It supports markdown, JSON, and YAML formats, offering a simple API for filtering, sorting, and managing structured data files with automatic validation and serialization.

### Quick Start

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
    format="markdown",
    body_field="content",
)

# Query and iterate
recent = posts.filter(lambda p: not p.draft).order_by("-date").head(3)
for post in recent:
    print(post.title)

# Add new items
new_post = BlogPost(
    title="Hello World",
    date=date.today(),
    tags=["intro"],
    content="# Hello\n\nIt works!",
)
posts.add(new_post)
```

### API Reference

**Query Methods**

- `filter(predicate)` - Filter items by predicate function
- `order_by(field)` - Sort by field (prefix with `-` for descending)
- `head(n=5)` / `tail(n=5)` - Get first/last n items
- `to_list()` - Materialize query to list
- `count()` - Count matching items
- `first()` / `last()` - Get first/last item or None
- `exists(predicate=None)` - Check if any items match
- `get(filename)` - Load specific file by name

**Lifecycle Methods**

- `add(model, path=None)` - Add new model to collection
- `update(model)` - Update existing model on disk
- `upsert(model)` - Add if new, update if exists
- `delete(target)` - Delete by model, filename, or Path
- `refresh(model)` - Reload model from disk
- `path_for(model)` - Get disk path for a model

Collections are iterable and return model instances.

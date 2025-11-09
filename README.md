## diskdantic

> Instead of having an ORM on top of a database, why not have a collection on top of a folder?

Disk-backed collections powered by Pydantic models. This is pretty much the whole API:

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
```

It's meant to work with markdown files, but it should also work with yaml/json.

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

## Why?

It makes it easier to write a custom CMS on top of your disk, which is nice. But it also feels like a fun thing that should exist.

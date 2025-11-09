import marimo

__generated_with = "0.17.7"
app = marimo.App(sql_output="polars")


@app.cell
def _():
    from datetime import date

    from pydantic import BaseModel

    from diskdantic import Collection

    return BaseModel, Collection, date


@app.cell
def _(BaseModel, Collection, date):
    class BlogPost(BaseModel):
        title: str
        date: date
        tags: list[str] = []
        draft: bool = False
        content: str

    posts = Collection(
        BlogPost,
        path="tests/fixtures/blog",
        body_field="content",
        format="markdown",
    )
    return BlogPost, posts


@app.cell
def _(posts):
    posts.to_list()[0]
    return


@app.cell
def _(BlogPost):
    post = BlogPost(title="lol", date="2015-01-01", tags=[], content="i am a blogpost yay!")
    return (post,)


@app.cell
def _(post, posts):
    posts.add(post)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()

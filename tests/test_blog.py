from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.blog import Blog, BlogCategory, BlogStatus
from tests.conftest import register_verified_user


async def _seed_category(title: str = "News", slug: str = "news") -> int:
    async with AsyncSessionLocal() as db:
        c = BlogCategory(title=title, slug=slug)
        db.add(c)
        await db.commit()
        return c.id


async def _seed_blog(
    *,
    author_id: int,
    title: str = "Post",
    slug: str = "post",
    status: BlogStatus = BlogStatus.publish,
    category_id: int | None = None,
    description: str = "Short description",
    enable_comment: bool = True,
) -> int:
    async with AsyncSessionLocal() as db:
        b = Blog(
            author_id=author_id,
            title=title,
            slug=slug,
            image="/media/blog/x.png",
            description=description,
            content="Full content body",
            status=status,
            category_id=category_id,
            enable_comment=enable_comment,
        )
        db.add(b)
        await db.commit()
        return b.id


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_index_only_published(client: AsyncClient):
    _, author = await register_verified_user(client)
    cat = await _seed_category()
    published = await _seed_blog(author_id=author, slug="p1", category_id=cat)
    await _seed_blog(author_id=author, slug="p2", status=BlogStatus.pending)

    r = await client.get("/api/v1/blogs")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["blogs"][0]["id"] == published
    assert body["blogs"][0]["category"] == "News"
    assert body["blogs"][0]["comment_count"] == 0
    assert body["blogs"][0]["author"]["full_name"] == "Test User"


async def test_index_category_filter_and_limit(client: AsyncClient):
    _, author = await register_verified_user(client)
    cat1 = await _seed_category("A", "a")
    cat2 = await _seed_category("B", "b")
    b1 = await _seed_blog(author_id=author, slug="a1", category_id=cat1)
    await _seed_blog(author_id=author, slug="b1", category_id=cat2)

    only_cat1 = (await client.get(f"/api/v1/blogs?cat={cat1}")).json()
    assert {b["id"] for b in only_cat1["blogs"]} == {b1}

    limited = (await client.get("/api/v1/blogs?limit=1")).json()
    assert limited["count"] == 1


async def test_description_truncated(client: AsyncClient):
    _, author = await register_verified_user(client)
    long_desc = "word " * 100  # ~500 chars
    await _seed_blog(author_id=author, description=long_desc)
    body = (await client.get("/api/v1/blogs")).json()
    desc = body["blogs"][0]["description"]
    assert desc.endswith("...")
    assert len(desc) <= 170


async def test_categories_listed(client: AsyncClient):
    await _seed_category("News", "news")
    r = await client.get("/api/v1/blogs/categories")
    assert r.status_code == 200
    assert r.json()[0]["title"] == "News"


async def test_show_with_comments(client: AsyncClient):
    token, author = await register_verified_user(client)
    blog_id = await _seed_blog(author_id=author)

    r = await client.post(
        f"/api/v1/blogs/{blog_id}/comments",
        headers=_auth(token),
        json={"comment": "Great post"},
    )
    assert r.status_code == 200

    show = (await client.get(f"/api/v1/blogs/{blog_id}")).json()["blog"]
    assert show["content"] == "Full content body"
    assert show["comment_count"] == 1
    assert len(show["comments"]) == 1
    assert show["comments"][0]["comment"] == "Great post"


async def test_comment_reply_threading(client: AsyncClient):
    token, author = await register_verified_user(client)
    blog_id = await _seed_blog(author_id=author)
    await client.post(
        f"/api/v1/blogs/{blog_id}/comments", headers=_auth(token), json={"comment": "root"}
    )
    show = (await client.get(f"/api/v1/blogs/{blog_id}")).json()["blog"]
    root_id = show["comments"][0]["id"]

    await client.post(
        f"/api/v1/blogs/{blog_id}/comments",
        headers=_auth(token),
        json={"comment": "a reply", "reply_id": root_id},
    )
    show = (await client.get(f"/api/v1/blogs/{blog_id}")).json()["blog"]
    assert show["comment_count"] == 2
    assert len(show["comments"]) == 1  # reply nested, not a root
    assert show["comments"][0]["replies"][0]["comment"] == "a reply"


async def test_show_pending_404(client: AsyncClient):
    _, author = await register_verified_user(client)
    blog_id = await _seed_blog(author_id=author, status=BlogStatus.pending)
    assert (await client.get(f"/api/v1/blogs/{blog_id}")).status_code == 404


async def test_comment_when_disabled_400(client: AsyncClient):
    token, author = await register_verified_user(client)
    blog_id = await _seed_blog(author_id=author, enable_comment=False)
    r = await client.post(
        f"/api/v1/blogs/{blog_id}/comments", headers=_auth(token), json={"comment": "hi"}
    )
    assert r.status_code == 400


async def test_comment_requires_auth(client: AsyncClient):
    _, author = await register_verified_user(client)
    blog_id = await _seed_blog(author_id=author)
    r = await client.post(f"/api/v1/blogs/{blog_id}/comments", json={"comment": "hi"})
    assert r.status_code == 401

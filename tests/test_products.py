from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.product import Product, ProductCategory, ProductStatus, ProductType
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _teacher(client: AsyncClient, email: str = "teacher@aiacademy.tj") -> tuple[str, int]:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()
    return token, uid


async def _seed_category(title: str = "Books", parent_id: int | None = None) -> int:
    async with AsyncSessionLocal() as db:
        cat = ProductCategory(title=title, parent_id=parent_id, order=1)
        db.add(cat)
        await db.commit()
        return cat.id


async def _seed_product(
    creator_id: int,
    *,
    title: str = "E-book",
    status: ProductStatus = ProductStatus.active,
    ordering: bool = True,
    category_id: int | None = None,
) -> int:
    async with AsyncSessionLocal() as db:
        product = Product(
            creator_id=creator_id,
            category_id=category_id,
            title=title,
            description="A nice product",
            type=ProductType.virtual,
            price=20,
            status=status,
            ordering=ordering,
        )
        db.add(product)
        await db.commit()
        return product.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_public_list_and_show(client: AsyncClient):
    token, uid = await _teacher(client)
    cat = await _seed_category()
    pid = await _seed_product(uid, category_id=cat)
    # a draft / non-ordering product must not appear
    await _seed_product(uid, title="Hidden", status=ProductStatus.draft)
    await _seed_product(uid, title="NoOrder", ordering=False)

    r = await client.get("/api/v1/products")
    assert r.status_code == 200
    assert [p["title"] for p in r.json()] == ["E-book"]
    assert r.json()[0]["category_title"] == "Books"

    detail = await client.get(f"/api/v1/products/{pid}")
    assert detail.status_code == 200
    assert detail.json()["description"] == "A nice product"


async def test_list_filtered_by_category(client: AsyncClient):
    token, uid = await _teacher(client)
    books = await _seed_category("Books")
    music = await _seed_category("Music")
    await _seed_product(uid, title="Book", category_id=books)
    await _seed_product(uid, title="Song", category_id=music)

    r = await client.get("/api/v1/products", params={"category_id": books})
    assert [p["title"] for p in r.json()] == ["Book"]


async def test_product_categories_tree(client: AsyncClient):
    top = await _seed_category("Books")
    await _seed_category("Fiction", parent_id=top)
    r = await client.get("/api/v1/product_categories")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert [s["title"] for s in body["categories"][0]["sub_categories"]] == ["Fiction"]


async def test_show_inactive_product_404(client: AsyncClient):
    token, uid = await _teacher(client)
    pid = await _seed_product(uid, status=ProductStatus.draft)
    r = await client.get(f"/api/v1/products/{pid}")
    assert r.status_code == 404


async def test_store_products_owner_scoped(client: AsyncClient):
    a_token, a_uid = await _teacher(client, email="a@aiacademy.tj")
    b_token, b_uid = await _teacher(client, email="b@aiacademy.tj")
    await _seed_product(a_uid, title="A-prod")
    await _seed_product(b_uid, title="B-prod")

    r = await client.get("/api/v1/panel/store/products", headers=_auth(a_token))
    assert r.status_code == 200
    assert [p["title"] for p in r.json()] == ["A-prod"]


async def test_store_products_requires_teacher(client: AsyncClient):
    token, _ = await register_verified_user(client, email="plain@aiacademy.tj")
    r = await client.get("/api/v1/panel/store/products", headers=_auth(token))
    assert r.status_code == 403

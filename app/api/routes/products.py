from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, require_level
from app.models.product import Product
from app.models.user import User
from app.repositories import products as products_repo
from app.schemas.common import error_responses
from app.schemas.product import (
    ProductCategoryList,
    ProductCategoryRead,
    ProductDetail,
    ProductRead,
)

router = APIRouter(tags=["store"])

TeacherUser = Annotated[User, Depends(require_level("teacher"))]


def _read(product: Product) -> ProductRead:
    return ProductRead(
        id=product.id,
        title=product.title,
        thumbnail=product.thumbnail,
        type=product.type,
        status=product.status,
        price=float(product.price) if product.price is not None else None,
        point=product.point,
        category_title=product.category.title if product.category else None,
        category_id=product.category_id,
        unlimited_inventory=product.unlimited_inventory,
        inventory=product.inventory,
        delivery_fee=float(product.delivery_fee) if product.delivery_fee is not None else None,
        created_at=product.created_at,
    )


@router.get("/products", response_model=list[ProductRead])
async def list_products(db: DbSession, category_id: int | None = Query(None)) -> list[ProductRead]:
    """Active, orderable store products (legacy Web\\ProductController@index)."""
    products = await products_repo.list_active(db, category_id)
    return [_read(p) for p in products]


@router.get(
    "/products/{product_id}",
    response_model=ProductDetail,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def show_product(product_id: int, db: DbSession) -> ProductDetail:
    product = await products_repo.get_active(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductDetail(**_read(product).model_dump(), description=product.description)


@router.get("/product_categories", response_model=ProductCategoryList)
async def list_product_categories(db: DbSession) -> ProductCategoryList:
    categories = await products_repo.list_categories(db)
    tops, children = products_repo.group_categories(categories)
    out = [
        ProductCategoryRead(
            id=top.id,
            title=top.title,
            icon=top.icon,
            sub_categories=[
                ProductCategoryRead(id=sub.id, title=sub.title, icon=sub.icon)
                for sub in children.get(top.id, [])
            ],
        )
        for top in tops
    ]
    return ProductCategoryList(count=len(out), categories=out)


@router.get("/panel/store/products", response_model=list[ProductRead])
async def my_products(current_user: TeacherUser, db: DbSession) -> list[ProductRead]:
    """The instructor's own products (legacy store/products)."""
    products = await products_repo.list_by_creator(db, current_user.id)
    return [_read(p) for p in products]

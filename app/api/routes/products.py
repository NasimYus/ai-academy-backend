from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, require_level
from app.models.product import Product
from app.models.product_order import ProductOrder
from app.models.user import User
from app.repositories import orders as orders_repo
from app.repositories import product_orders as product_orders_repo
from app.repositories import products as products_repo
from app.schemas.common import error_responses
from app.schemas.order import OrderRead
from app.schemas.product import (
    ProductCategoryList,
    ProductCategoryRead,
    ProductDetail,
    ProductRead,
)
from app.schemas.product_order import ProductOrderCreate, ProductOrderRead
from app.services.order_presenter import order_read

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


@router.post(
    "/products/{product_id}/pay",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def pay_product(
    product_id: int, payload: ProductOrderCreate, current_user: CurrentUser, db: DbSession
) -> OrderRead:
    """Buy a product: create a pending ProductOrder + order (legacy store checkout).

    Settling it via /payments records a `product` Sale and advances the
    ProductOrder (virtual → success, physical → waiting_delivery)."""
    product = await products_repo.get_active(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    unit_price = float(product.price or 0)
    if unit_price <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_free")

    delivery = float(product.delivery_fee or 0)
    total = unit_price * payload.quantity + delivery

    product_order = ProductOrder(
        product_id=product.id,
        seller_id=product.creator_id,
        buyer_id=current_user.id,
        quantity=payload.quantity,
        message_to_seller=payload.message_to_seller,
    )
    db.add(product_order)
    await db.flush()

    order = await orders_repo.create(
        db,
        user_id=current_user.id,
        amount=total,
        total_discount=0,
        total_amount=total,
        items=[
            {
                "product_id": product.id,
                "product_order_id": product_order.id,
                "amount": total,
                "total_amount": total,
            }
        ],
    )
    return order_read(order)


@router.get(
    "/panel/product-orders",
    response_model=list[ProductOrderRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def my_product_orders(current_user: CurrentUser, db: DbSession) -> list[ProductOrderRead]:
    """The buyer's store orders + their delivery status."""
    rows = await product_orders_repo.list_for_buyer(db, current_user.id)
    return [
        ProductOrderRead(
            id=po.id,
            product_id=po.product_id,
            title=po.product.title if po.product else None,
            quantity=po.quantity,
            status=po.status,
            tracking_code=po.tracking_code,
            created_at=po.created_at,
        )
        for po in rows
    ]

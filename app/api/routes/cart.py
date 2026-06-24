from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.cart import CartItem
from app.models.course import CourseStatus
from app.repositories import cart as cart_repo
from app.repositories import courses as courses_repo
from app.schemas.cart import AddToCartRequest, CartAmounts, CartItemRead, CartRead
from app.schemas.common import error_responses
from app.services import access

router = APIRouter(prefix="/cart", tags=["cart"])


def _item_read(item: CartItem) -> CartItemRead:
    course = item.course
    return CartItemRead(
        id=item.id,
        type="webinar",
        course_id=course.id,
        title=course.title,
        slug=course.slug,
        thumbnail=course.thumbnail,
        teacher_name=course.teacher.full_name if course.teacher else None,
        price=float(course.price),
        created_at=item.created_at,
    )


def _amounts(items: list[CartItem]) -> CartAmounts:
    # Coupons/tax/commission land in 4.2/4.3; for now total == sub_total.
    sub_total = sum(float(i.course.price) for i in items)
    return CartAmounts(sub_total=sub_total, total_discount=0, tax_price=0, total=sub_total)


@router.get("", response_model=CartRead, responses=error_responses(status.HTTP_401_UNAUTHORIZED))
async def list_cart(current_user: CurrentUser, db: DbSession) -> CartRead:
    """The user's cart (legacy CartController@index)."""
    items = await cart_repo.list_for_user(db, current_user.id)
    return CartRead(items=[_item_read(i) for i in items], amounts=_amounts(items))


@router.post(
    "",
    response_model=CartItemRead,
    responses=error_responses(
        status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND
    ),
)
async def add_to_cart(
    payload: AddToCartRequest, current_user: CurrentUser, db: DbSession
) -> CartItemRead:
    """Add a course to the cart (legacy AddCartController@store, webinar branch)."""
    course = await courses_repo.get_by_id(db, payload.item_id)
    if course is None or course.status != CourseStatus.active or course.private:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if await access.has_course_access(db, current_user, course):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="already_purchased")
    if await cart_repo.exists(db, user_id=current_user.id, course_id=course.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="already_in_cart")

    item = await cart_repo.add(db, user_id=current_user.id, course_id=course.id)
    return _item_read(item)


@router.delete(
    "/{item_id}",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def remove_from_cart(
    item_id: int, current_user: CurrentUser, db: DbSession
) -> dict[str, str]:
    """Remove an item from the cart (legacy CartController@destroy, scoped to owner)."""
    item = await cart_repo.get_owned(db, item_id, current_user.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    await cart_repo.remove(db, item)
    return {"status": "ok"}

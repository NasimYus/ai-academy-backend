from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.bundle import Bundle
from app.models.enrollment import EnrollmentSource
from app.models.reward import RewardStatus
from app.repositories import bundles as bundles_repo
from app.repositories import enrollments as enrollments_repo
from app.repositories import orders as orders_repo
from app.repositories import rewards as rewards_repo
from app.schemas.bundle import BundleDetail, BundlePublicRead, BundlePurchaseResponse
from app.schemas.common import error_responses
from app.schemas.course import CourseRead
from app.schemas.order import OrderRead
from app.services.course_presenter import to_brief
from app.services.order_presenter import order_read

router = APIRouter(prefix="/bundles", tags=["bundles"])


def _public(bundle: Bundle) -> BundlePublicRead:
    return BundlePublicRead(
        id=bundle.id,
        title=bundle.title,
        slug=bundle.slug,
        thumbnail=bundle.thumbnail,
        image_cover=bundle.image_cover,
        price=float(bundle.price) if bundle.price is not None else None,
        points=bundle.points,
        category=bundle.category.title if bundle.category else None,
        webinars_count=len(bundle.webinars),
        created_at=bundle.created_at,
    )


@router.get("", response_model=list[BundlePublicRead])
async def list_bundles(db: DbSession) -> list[BundlePublicRead]:
    """Active bundles for the public catalogue."""
    bundles = await bundles_repo.list_active(db)
    return [_public(b) for b in bundles]


@router.get(
    "/{bundle_id}",
    response_model=BundleDetail,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def show_bundle(bundle_id: int, db: DbSession) -> BundleDetail:
    bundle = await bundles_repo.get_active(db, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found")
    courses = [
        to_brief(bw.course)
        for bw in sorted(bundle.webinars, key=lambda w: w.order or 0)
        if bw.course is not None and bw.course.status.value == "active"
    ]
    return BundleDetail(**_public(bundle).model_dump(), courses=courses)


@router.get(
    "/{bundle_id}/webinars",
    response_model=list[CourseRead],
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def bundle_webinars(bundle_id: int, db: DbSession) -> list[CourseRead]:
    bundle = await bundles_repo.get_active(db, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found")
    return [
        to_brief(bw.course)
        for bw in sorted(bundle.webinars, key=lambda w: w.order or 0)
        if bw.course is not None and bw.course.status.value == "active"
    ]


async def _grant(db: DbSession, user_id: int, bundle_id: int) -> None:
    """Enroll the user in every bundle course they don't already have (source=bundle)."""
    target = await bundles_repo.active_course_ids(db, bundle_id)
    owned = set(await enrollments_repo.course_ids_for_user(db, user_id))
    missing = [cid for cid in target if cid not in owned]
    if not missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="already_purchased"
        )
    for course_id in missing:
        await enrollments_repo.create(
            db, user_id=user_id, course_id=course_id, source=EnrollmentSource.bundle
        )


@router.post(
    "/{bundle_id}/free",
    response_model=BundlePurchaseResponse,
    responses=error_responses(status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_CONTENT),
)
async def buy_free_bundle(
    bundle_id: int, current_user: CurrentUser, db: DbSession
) -> BundlePurchaseResponse:
    """Enroll in a free bundle's courses (legacy BundleController@free)."""
    bundle = await bundles_repo.get_active(db, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found")
    if bundle.price and float(bundle.price) > 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_free")
    await _grant(db, current_user.id, bundle_id)
    return BundlePurchaseResponse(message="enrolled")


@router.post(
    "/{bundle_id}/buyWithPoint",
    response_model=BundlePurchaseResponse,
    responses=error_responses(status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_CONTENT),
)
async def buy_bundle_with_points(
    bundle_id: int, current_user: CurrentUser, db: DbSession
) -> BundlePurchaseResponse:
    """Redeem points for a bundle (legacy BundleController@buyWithPoint)."""
    bundle = await bundles_repo.get_active(db, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found")
    if not bundle.points:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="no_points")

    available = (await rewards_repo.points(db, current_user.id))["available"]
    if available < bundle.points:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="no_enough_points"
        )

    await _grant(db, current_user.id, bundle_id)
    await rewards_repo.create_entry(
        db,
        user_id=current_user.id,
        score=bundle.points,
        type="withdraw",
        status=RewardStatus.deduction,
        item_id=bundle.id,
    )
    return BundlePurchaseResponse(message="paid")


@router.post(
    "/{bundle_id}/pay",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def pay_bundle(bundle_id: int, current_user: CurrentUser, db: DbSession) -> OrderRead:
    """Create a pending order for a paid bundle (legacy fakeCart → checkout).

    Settle it via the normal /payments flow; on `paid`, `payments.complete`
    records a `bundle` Sale and enrolls the buyer in every bundle course."""
    bundle = await bundles_repo.get_active(db, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found")

    price = float(bundle.price or 0)
    if price <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_free")

    target = await bundles_repo.active_course_ids(db, bundle_id)
    owned = set(await enrollments_repo.course_ids_for_user(db, current_user.id))
    if target and all(cid in owned for cid in target):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="already_purchased"
        )

    order = await orders_repo.create(
        db,
        user_id=current_user.id,
        amount=price,
        total_discount=0,
        total_amount=price,
        items=[{"bundle_id": bundle_id, "amount": price, "total_amount": price}],
    )
    return order_read(order)

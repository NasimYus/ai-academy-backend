from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.models.role import Role
from app.repositories import certificates as certificates_repo
from app.repositories import courses as courses_repo
from app.repositories import enrollments as enrollments_repo
from app.repositories import favorites as favorites_repo
from app.repositories import follows as follows_repo
from app.repositories import meetings as meetings_repo
from app.repositories import orders as orders_repo
from app.repositories import quizzes as quizzes_repo
from app.repositories import sales as sales_repo
from app.schemas.common import error_responses
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/panel", tags=["dashboard"])

_INSTRUCTOR_ROLES = {Role.TEACHER, Role.ORGANIZATION, Role.ADMIN}


@router.get(
    "/dashboard",
    response_model=DashboardSummary,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def dashboard(current_user: CurrentUser, db: DbSession) -> DashboardSummary:
    """Panel home aggregates (legacy DashboardController): the buyer's learning +
    purchase counts, plus sales/teaching counts for instructors."""
    enrolled = await enrollments_repo.list_courses_for_user(db, current_user.id)
    purchases = await orders_repo.paid_items_for_user(db, current_user.id)
    favorites = await favorites_repo.list_for_user(db, current_user.id)
    passed_quizzes = await quizzes_repo.passed_results_for_user(db, current_user.id)

    summary = DashboardSummary(
        is_instructor=current_user.role_name in _INSTRUCTOR_ROLES,
        enrolled_count=len(enrolled),
        purchases_count=len(purchases),
        favorites_count=len(favorites),
        meetings_count=await meetings_repo.open_reservations_count(db, current_user.id),
        certificates_count=await certificates_repo.count_for_student(db, current_user.id),
        passed_quizzes_count=len(passed_quizzes),
        following_count=await follows_repo.following_count(db, current_user.id),
    )

    if summary.is_instructor:
        sales = await sales_repo.seller_sales(db, current_user.id)
        requests = await meetings_repo.requests_for_creator(db, current_user.id)
        summary.sales_count = len(sales)
        summary.sales_income = await sales_repo.seller_income(db, current_user.id)
        summary.meeting_requests_count = len(requests)
        summary.courses_count = len(await courses_repo.list_by_creator(db, current_user.id))

    return summary

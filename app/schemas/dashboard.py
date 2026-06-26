from pydantic import BaseModel


class DashboardSummary(BaseModel):
    """Panel dashboard aggregates (legacy Panel\\DashboardController)."""

    is_instructor: bool
    # Student-side
    enrolled_count: int
    purchases_count: int
    favorites_count: int
    # Instructor-side (zero for plain students)
    courses_count: int = 0
    sales_count: int = 0
    sales_income: float = 0
    meeting_requests_count: int = 0

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    """Panel dashboard aggregates (legacy Panel\\DashboardController)."""

    is_instructor: bool
    # Student-side
    enrolled_count: int
    purchases_count: int
    favorites_count: int
    # Sidebar avatar counters (legacy: classes + following)
    following_count: int = 0
    # Student hello-box counters (legacy getStudentHelloBoxData)
    meetings_count: int = 0
    certificates_count: int = 0
    passed_quizzes_count: int = 0
    # Wallet card (legacy authUserBalanceCharge). NOTE(Phase): the accounting/
    # financial subsystem is not yet migrated — 0 on a clean DB, as in legacy.
    balance: float = 0
    # Instructor-side (zero for plain students)
    courses_count: int = 0
    sales_count: int = 0
    sales_income: float = 0
    meeting_requests_count: int = 0

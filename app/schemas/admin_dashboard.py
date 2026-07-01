from datetime import datetime

from pydantic import BaseModel


class ChartData(BaseModel):
    labels: list[str]
    data: list[float]


class GrowStat(BaseModel):
    amount: float
    grow_percent: str  # "No previous value" or e.g. "12.5%"
    grow_status: str  # up | down


class DailySalesByType(BaseModel):
    """Today's sales split by course type (legacy dailySalesTypeStatistics)."""

    webinars: int
    courses: int
    appointments: int
    total: int


class PeriodStats(BaseModel):
    today: float
    month: float
    year: float
    total: float


class RecentComment(BaseModel):
    id: int
    user_name: str | None = None
    comment: str | None = None
    created_at: datetime


class RecentTicket(BaseModel):
    id: int
    title: str
    status: str
    created_at: datetime


class RecentCourseRow(BaseModel):
    id: int
    title: str
    teacher_name: str | None = None
    status: str


class AdminDashboard(BaseModel):
    """Admin general dashboard (legacy Admin\\DashboardController@index)."""

    daily_sales_by_type: DailySalesByType
    income: PeriodStats
    sales_counts: PeriodStats
    new_sales: int
    new_comments: int
    new_tickets: int
    pending_reviews: int
    sales_chart_year: ChartData  # month_of_year (12)
    sales_chart_month: ChartData  # day_of_month (31)
    sales_stats: dict[str, GrowStat]  # today | week | month | year
    recent_comments: list[RecentComment]
    recent_tickets: list[RecentTicket]
    recent_tickets_pending: int
    recent_webinars: list[RecentCourseRow]
    recent_webinars_pending: int
    recent_courses: list[RecentCourseRow]
    recent_courses_pending: int
    users_chart: ChartData

"""Admin marketing dashboard schemas (parity of Admin\\DashboardController@marketing
+ DashboardTrait marketing helpers)."""

from pydantic import BaseModel

from app.schemas.admin_dashboard import ChartData, GrowStat


class TopClassRow(BaseModel):
    id: int
    title: str
    sales_count: int
    sales_amount: float


class TopAppointmentRow(BaseModel):
    id: int
    consultant_name: str | None
    sales_count: int
    sales_amount: float


class TopSellerRow(BaseModel):
    id: int
    name: str | None
    classes_duration: int  # minutes, summed across active classes
    sales_count: int
    sales_amount: float


class ActiveStudentRow(BaseModel):
    id: int
    name: str | None
    purchased_classes: int
    reserved_appointments: int
    total_cost: float


class AdminMarketing(BaseModel):
    # top counters
    users_without_purchases: int
    teachers_without_class: int
    featured_classes: int
    active_discounts: int
    # charts
    classes_statistics: ChartData  # % split by course type
    net_profit_chart_year: ChartData
    net_profit_chart_month: ChartData
    net_profit_stats: dict[str, GrowStat]  # today / week / month / year
    # tables
    top_selling_classes: list[TopClassRow]
    top_selling_appointments: list[TopAppointmentRow]
    top_selling_teachers: list[TopSellerRow]
    top_selling_organizations: list[TopSellerRow]
    most_active_students: list[ActiveStudentRow]

from datetime import datetime

from pydantic import BaseModel

from app.models.registration_package import PackageRole, PackageStatus

# Parity of legacy Api\RegistrationPackage::details + RegistrationPackagesController@index.
# Null count/`days` mean "unlimited" (legacy `?? 'unlimited'`).


class RegistrationPackageRead(BaseModel):
    id: int
    role: PackageRole
    title: str
    description: str | None = None
    icon: str | None = None
    days: int | None = None
    price: float
    instructors_count: int | None = None
    students_count: int | None = None
    courses_capacity: int | None = None
    courses_count: int | None = None
    meeting_count: int | None = None
    status: PackageStatus
    is_active: bool = False


class ActivePackage(BaseModel):
    package_id: int
    title: str
    activation_date: datetime
    days_remained: int | None = None  # null = unlimited
    instructors_count: int | None = None
    students_count: int | None = None
    courses_capacity: int | None = None
    courses_count: int | None = None
    meeting_count: int | None = None


class PackageList(BaseModel):
    packages: list[RegistrationPackageRead]
    active_package: ActivePackage | None = None


class PackageResponse(BaseModel):
    message: str

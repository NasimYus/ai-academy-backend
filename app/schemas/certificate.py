from datetime import datetime

from pydantic import BaseModel

# Parity with legacy Api\Certificate brief/details + CertificatesController.


class CertificateBrief(BaseModel):
    id: int
    user_grade: int | None = None
    file: str | None = None  # rendered PDF url (null until first download)
    created_at: datetime


class Achievement(BaseModel):
    """Legacy CertificatesController@achievements: a passed result + its certificate."""

    quiz_result_id: int
    quiz_id: int
    quiz_title: str
    course_id: int
    course_title: str | None = None
    user_grade: int | None = None
    status: str
    certificate: CertificateBrief | None = None


class ValidatedCertificate(BaseModel):
    id: int
    student_name: str | None = None
    quiz_title: str | None = None
    course_title: str | None = None
    date: datetime


class CertificateValidation(BaseModel):
    is_valid: bool
    certificate: ValidatedCertificate | None = None

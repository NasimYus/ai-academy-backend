from datetime import datetime

from pydantic import BaseModel

# Parity with legacy Api\Certificate brief/details + CertificatesController.


class InstructorCertificateSource(BaseModel):
    """A certificate-issuing quiz of the instructor (legacy certificates list row)."""

    quiz_id: int
    quiz_title: str
    course_id: int | None = None
    course_title: str | None = None
    certificates_count: int = 0


class InstructorCertificatesList(BaseModel):
    certificates_count: int
    students_count: int
    sources: list[InstructorCertificateSource] = []


class IssuedCertificate(BaseModel):
    """A certificate earned by a student on the instructor's quiz (all_students)."""

    id: int
    student_name: str | None = None
    quiz_title: str | None = None
    course_title: str | None = None
    user_grade: int | None = None
    file: str | None = None
    created_at: datetime


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

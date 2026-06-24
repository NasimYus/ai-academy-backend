from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.models.quiz import ResultStatus
from app.repositories import certificates as certificates_repo
from app.repositories import courses as courses_repo
from app.repositories import quizzes as quizzes_repo
from app.schemas.certificate import (
    Achievement,
    CertificateBrief,
    CertificateValidation,
    ValidatedCertificate,
)
from app.schemas.common import error_responses
from app.services import certificates as certificates_service

router = APIRouter(tags=["certificates"])


def _brief(certificate) -> CertificateBrief:
    return CertificateBrief(
        id=certificate.id,
        user_grade=certificate.user_grade,
        file=certificate.file,
        created_at=certificate.created_at,
    )


@router.get("/panel/certificates/achievements", response_model=list[Achievement])
async def achievements(current_user: CurrentUser, db: DbSession) -> list[Achievement]:
    """Passed quizzes with their certificate, if issued (legacy achievements)."""
    results = await quizzes_repo.passed_results_for_user(db, current_user.id)
    certs = await certificates_repo.by_result_ids(db, [r.id for r in results])

    course_titles: dict[int, str | None] = {}
    out: list[Achievement] = []
    for r in results:
        quiz = r.quiz
        if quiz.course_id not in course_titles:
            course = await courses_repo.get_by_id(db, quiz.course_id)
            course_titles[quiz.course_id] = course.title if course else None
        cert = certs.get(r.id)
        out.append(
            Achievement(
                quiz_result_id=r.id,
                quiz_id=quiz.id,
                quiz_title=quiz.title,
                course_id=quiz.course_id,
                course_title=course_titles[quiz.course_id],
                user_grade=r.user_grade,
                status=r.status.value,
                certificate=_brief(cert) if cert else None,
            )
        )
    return out


@router.get(
    "/panel/quizzes/results/{quiz_result_id}/show",
    response_class=FileResponse,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def show_certificate(
    quiz_result_id: int, current_user: CurrentUser, db: DbSession
) -> FileResponse:
    """Render (or return cached) the certificate PDF (legacy makeCertificate)."""
    result = await quizzes_repo.get_user_result(db, quiz_result_id, current_user.id)
    if result is None or result.status != ResultStatus.passed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    quiz = await quizzes_repo.get_by_id(db, result.quiz_id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    certificate = await certificates_service.issue_if_passed(db, quiz, result)
    if certificate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No certificate")

    if not certificate.file:
        course = await courses_repo.get_by_id(db, quiz.course_id)
        certificate.file = certificates_service.render_pdf(
            certificate,
            student_name=current_user.full_name or current_user.email,
            quiz_title=quiz.title,
            course_title=course.title if course else None,
        )
        await db.commit()

    disk_path = Path(settings.media_root) / certificate.file.removeprefix(f"{settings.media_url}/")
    return FileResponse(disk_path, media_type="application/pdf", filename=disk_path.name)


@router.get("/certificate_validation", response_model=CertificateValidation)
async def validate_certificate(
    db: DbSession, certificate_id: int = Query(...)
) -> CertificateValidation:
    """Public certificate validation (legacy CertificatesController@checkValidate)."""
    certificate = await certificates_repo.get_by_id(db, certificate_id)
    if certificate is None:
        return CertificateValidation(is_valid=False, certificate=None)

    course = await courses_repo.get_by_id(db, certificate.quiz.course_id)
    return CertificateValidation(
        is_valid=True,
        certificate=ValidatedCertificate(
            id=certificate.id,
            student_name=certificate.student.full_name,
            quiz_title=certificate.quiz.title,
            course_title=course.title if course else None,
            date=certificate.created_at,
        ),
    )

"""Certificate issuance + rendering — parity of CertificatesController / MakeCertificate.

A certificate is issued when a user passes a quiz flagged `certificate`. The PDF
is rendered synchronously on first download (no template positioning — that is
instructor/admin, Phase 6) and cached on disk.
"""

from pathlib import Path

from fpdf import FPDF
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.certificate import Certificate
from app.models.quiz import Quiz, QuizResult, ResultStatus
from app.repositories import certificates as certificates_repo


def _latin1(text: str) -> str:
    # fpdf2 core fonts are latin-1 only. NOTE(F.6): embed a Unicode TTF to render
    # Cyrillic certificate text faithfully; for now non-latin chars degrade.
    return text.encode("latin-1", "replace").decode("latin-1")


async def issue_if_passed(
    db: AsyncSession, quiz: Quiz, quiz_result: QuizResult
) -> Certificate | None:
    """Create the achievement certificate once a certificate-quiz is passed."""
    if not quiz.certificate or quiz_result.status != ResultStatus.passed:
        return None
    existing = await certificates_repo.get_by_result(db, quiz_result.id)
    if existing is not None:
        return existing
    return await certificates_repo.create(
        db,
        quiz_id=quiz.id,
        quiz_result_id=quiz_result.id,
        student_id=quiz_result.user_id,
        user_grade=quiz_result.user_grade,
    )


def render_pdf(
    certificate: Certificate,
    *,
    student_name: str,
    quiz_title: str,
    course_title: str | None,
) -> str:
    """Render the certificate PDF to media and return its public path."""
    subdir = "certificates"
    filename = f"certificate-{certificate.id}.pdf"
    target_dir = Path(settings.media_root) / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    pdf.set_font("Helvetica", "B", 32)
    pdf.ln(20)
    pdf.cell(0, 20, "Certificate of Achievement", align="C")
    pdf.ln(30)

    pdf.set_font("Helvetica", "", 16)
    pdf.cell(0, 10, "This certifies that", align="C")
    pdf.ln(14)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 12, _latin1(student_name or "Student"), align="C")
    pdf.ln(18)

    pdf.set_font("Helvetica", "", 16)
    pdf.cell(0, 10, "has successfully completed", align="C")
    pdf.ln(12)
    pdf.set_font("Helvetica", "B", 18)
    title = quiz_title if not course_title else f"{quiz_title} - {course_title}"
    pdf.cell(0, 10, _latin1(title), align="C")
    pdf.ln(18)

    pdf.set_font("Helvetica", "", 12)
    grade = f"Grade: {certificate.user_grade}" if certificate.user_grade is not None else ""
    date = certificate.created_at.strftime("%d %B %Y")
    pdf.cell(0, 8, f"{grade}    Date: {date}    Certificate ID: {certificate.id}", align="C")

    pdf.output(str(target_dir / filename))
    return f"{settings.media_url}/{subdir}/{filename}"

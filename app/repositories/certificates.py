from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.certificate import Certificate
from app.models.course import Course
from app.models.quiz import Quiz
from app.models.user import User


async def instructor_sources(db: AsyncSession, creator_id: int) -> list[tuple]:
    """Instructor's certificate-quizzes + issued count (legacy certificates list)."""
    result = await db.execute(
        select(
            Quiz.id,
            Quiz.title,
            Quiz.course_id,
            Course.title,
            func.count(Certificate.id),
        )
        .select_from(Quiz)
        .outerjoin(Course, Course.id == Quiz.course_id)
        .outerjoin(Certificate, Certificate.quiz_id == Quiz.id)
        .where(Quiz.creator_id == creator_id, Quiz.certificate.is_(True))
        .group_by(Quiz.id, Course.title)
        .order_by(Quiz.id.desc())
    )
    return list(result.all())


async def instructor_certificates(db: AsyncSession, creator_id: int) -> list[tuple]:
    """Certificates issued to students on the instructor's quizzes (legacy all_students)."""
    result = await db.execute(
        select(Certificate, User.full_name, Quiz.title, Course.title)
        .select_from(Certificate)
        .join(Quiz, Quiz.id == Certificate.quiz_id)
        .join(User, User.id == Certificate.student_id)
        .outerjoin(Course, Course.id == Quiz.course_id)
        .where(Quiz.creator_id == creator_id)
        .order_by(Certificate.created_at.desc())
    )
    return list(result.all())


async def count_for_creator(db: AsyncSession, creator_id: int) -> int:
    result = await db.execute(
        select(func.count(Certificate.id))
        .select_from(Certificate)
        .join(Quiz, Quiz.id == Certificate.quiz_id)
        .where(Quiz.creator_id == creator_id)
    )
    return int(result.scalar_one())


async def count_for_student(db: AsyncSession, student_id: int) -> int:
    """Legacy hello_box: Certificate::where('student_id', ...)->count()."""
    result = await db.execute(
        select(func.count()).select_from(Certificate).where(Certificate.student_id == student_id)
    )
    return int(result.scalar_one())


async def get_by_result(db: AsyncSession, quiz_result_id: int) -> Certificate | None:
    result = await db.execute(
        select(Certificate).where(Certificate.quiz_result_id == quiz_result_id)
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, certificate_id: int) -> Certificate | None:
    result = await db.execute(
        select(Certificate)
        .where(Certificate.id == certificate_id)
        .options(selectinload(Certificate.student), selectinload(Certificate.quiz))
    )
    return result.scalar_one_or_none()


async def by_result_ids(db: AsyncSession, result_ids: list[int]) -> dict[int, Certificate]:
    if not result_ids:
        return {}
    result = await db.execute(select(Certificate).where(Certificate.quiz_result_id.in_(result_ids)))
    return {c.quiz_result_id: c for c in result.scalars().all()}


async def create(
    db: AsyncSession,
    *,
    quiz_id: int,
    quiz_result_id: int,
    student_id: int,
    user_grade: int | None,
) -> Certificate:
    certificate = Certificate(
        quiz_id=quiz_id,
        quiz_result_id=quiz_result_id,
        student_id=student_id,
        user_grade=user_grade,
    )
    db.add(certificate)
    await db.commit()
    await db.refresh(certificate)
    return certificate

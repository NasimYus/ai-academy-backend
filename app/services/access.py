"""Course content access — parity of legacy Webinar::checkUserHasBought.

Access is granted to the course owner (creator/teacher) or an enrolled user.
Subscription / installment / gift / bundle sources are wired in Phase 4.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.user import User
from app.repositories import enrollments as enrollments_repo


async def has_course_access(db: AsyncSession, user: User | None, course: Course) -> bool:
    if user is None:
        return False
    if course.creator_id == user.id or course.teacher_id == user.id:
        return True
    return await enrollments_repo.exists(db, user_id=user.id, course_id=course.id)

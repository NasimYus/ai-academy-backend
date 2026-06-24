"""Presenter mapping Support ORM rows to the API schema (legacy Support->details).

Relationships are eager-loaded by the repository (`lazy="raise"`).
"""

from app.models.support import Support
from app.schemas.support import (
    SupportConversationRead,
    SupportCourseRef,
    SupportDetail,
    SupportType,
)
from app.schemas.user import UserBrief


def _conversation(conv) -> SupportConversationRead:
    return SupportConversationRead(
        message=conv.message,
        sender=UserBrief.model_validate(conv.sender) if conv.sender else None,
        supporter=UserBrief.model_validate(conv.supporter) if conv.supporter else None,
        attach=conv.attach,
        created_at=conv.created_at,
    )


def to_detail(support: Support) -> SupportDetail:
    course = support.course
    return SupportDetail(
        id=support.id,
        department=support.department.title if support.department else None,
        status=support.status,
        # legacy: course_support iff a course (webinar) is attached, else platform
        type=SupportType.course_support if support.course_id else SupportType.platform_support,
        title=support.title,
        course=(
            SupportCourseRef(
                id=course.id, title=course.title, slug=course.slug, image=course.thumbnail
            )
            if course
            else None
        ),
        user=UserBrief.model_validate(support.user),
        conversations=[_conversation(c) for c in support.conversations],
        created_at=support.created_at,
        updated_at=support.updated_at,
    )

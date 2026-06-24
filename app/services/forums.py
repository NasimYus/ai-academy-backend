"""Forum (Q&A) presentation — parity of WebinarForumResource / CourseForumAnswerResource
and the CourseForum/Answer policies (can pin/update/resolve)."""

from app.models.course import Course
from app.models.forum import CourseForum, CourseForumAnswer
from app.models.user import User
from app.schemas.forum import ForumAnswerRead, ForumCan, ForumThreadRead, LastAnswer
from app.schemas.user import UserBrief


def is_course_owner(course: Course, user: User) -> bool:
    return course.creator_id == user.id or course.teacher_id == user.id


def thread_read(forum: CourseForum, user: User, course: Course) -> ForumThreadRead:
    answers = sorted(forum.answers, key=lambda a: a.id)
    answers_count = len(answers)
    owner = is_course_owner(course, user)

    read = ForumThreadRead(
        id=forum.id,
        title=forum.title,
        description=forum.description,
        pin=forum.pin,
        attachment=forum.attach,
        answers_count=answers_count,
        resolved=any(a.resolved for a in answers),
        user=UserBrief.model_validate(forum.user) if forum.user else None,
        created_at=forum.created_at,
        can=ForumCan(pin=owner, update=forum.user_id == user.id),
    )

    if answers:
        last = answers[-1]
        seen: list[int] = []
        avatars: list[str] = []
        for a in answers:
            if a.user_id not in seen:
                seen.append(a.user_id)
                if len(avatars) < 3 and a.user and a.user.avatar:
                    avatars.append(a.user.avatar)
        read.active_users = avatars
        read.more = answers_count - min(len(seen), 3)
        read.last_activity = last.created_at
        read.last_answer = LastAnswer(
            description=last.description,
            user=UserBrief.model_validate(last.user) if last.user else None,
        )

    return read


def answer_read(
    answer: CourseForumAnswer, user: User, course: Course, thread_author_id: int
) -> ForumAnswerRead:
    owner = is_course_owner(course, user)
    return ForumAnswerRead(
        id=answer.id,
        description=answer.description,
        pin=answer.pin,
        resolved=answer.resolved,
        user=UserBrief.model_validate(answer.user) if answer.user else None,
        created_at=answer.created_at,
        can=ForumCan(
            pin=owner,
            resolve=owner or thread_author_id == user.id,
            update=answer.user_id == user.id,
        ),
    )

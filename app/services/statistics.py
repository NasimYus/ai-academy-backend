"""Instructor course statistics — parity of WebinarStatisticController (statistic=true).

Read-only aggregation across the course's content, enrolments, paid sales and
engagement, scoped to one course the instructor owns.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment, AssignmentStatus
from app.models.comment import Comment
from app.models.content import Chapter, ChapterStatus, CourseSession, File, TextLesson
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.forum import CourseForum
from app.models.order import Order, OrderItem, OrderStatus
from app.models.quiz import Quiz, QuizStatus
from app.models.review import CourseReview, ReviewStatus
from app.schemas.instructor import CourseStatistics


async def _count(db: AsyncSession, model, *where) -> int:
    result = await db.execute(select(func.count()).select_from(model).where(*where))
    return int(result.scalar_one())


async def build_course_statistics(db: AsyncSession, course: Course) -> CourseStatistics:
    cid = course.id

    sales = await db.execute(
        select(func.count(OrderItem.id), func.coalesce(func.sum(OrderItem.total_amount), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .where(OrderItem.course_id == cid, Order.status == OrderStatus.paid)
    )
    sales_count, sales_amount = sales.one()

    rate_row = await db.execute(
        select(func.coalesce(func.avg(CourseReview.rates), 0)).where(
            CourseReview.course_id == cid, CourseReview.status == ReviewStatus.active
        )
    )

    return CourseStatistics(
        students_count=await _count(db, Enrollment, Enrollment.course_id == cid),
        sales_count=int(sales_count),
        sales_amount=float(sales_amount),
        rate=round(float(rate_row.scalar_one()), 2),
        reviews_count=await _count(
            db,
            CourseReview,
            CourseReview.course_id == cid,
            CourseReview.status == ReviewStatus.active,
        ),
        comments_count=await _count(db, Comment, Comment.course_id == cid),
        chapters_count=await _count(
            db, Chapter, Chapter.course_id == cid, Chapter.status == ChapterStatus.active
        ),
        sessions_count=await _count(db, CourseSession, CourseSession.course_id == cid),
        files_count=await _count(db, File, File.course_id == cid),
        text_lessons_count=await _count(db, TextLesson, TextLesson.course_id == cid),
        quizzes_count=await _count(
            db, Quiz, Quiz.course_id == cid, Quiz.status == QuizStatus.active
        ),
        assignments_count=await _count(
            db,
            Assignment,
            Assignment.course_id == cid,
            Assignment.status == AssignmentStatus.active,
        ),
        forums_count=await _count(db, CourseForum, CourseForum.course_id == cid),
    )

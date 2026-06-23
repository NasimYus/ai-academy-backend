from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.comment import Comment, CommentStatus
from app.models.course import Course, CourseStatus, CourseType
from app.models.review import CourseReview, ReviewStatus
from app.models.role import Role
from app.models.user import User, UserStatus


async def _seed() -> str:
    async with AsyncSessionLocal() as db:
        user = User(
            full_name="Reviewer",
            email="r@x.tj",
            role_name=Role.USER,
            role_id=1,
            status=UserStatus.active,
        )
        db.add(user)
        course = Course(
            title="Reviewed",
            slug="reviewed",
            type=CourseType.course,
            status=CourseStatus.active,
            price=0,
        )
        db.add(course)
        await db.flush()
        db.add_all(
            [
                CourseReview(
                    course_id=course.id,
                    user_id=user.id,
                    content_quality=4,
                    instructor_skills=5,
                    purchase_worth=3,
                    support_quality=4,
                    rates=4,
                    description="Great",
                    status=ReviewStatus.active,
                ),
                CourseReview(
                    course_id=course.id,
                    user_id=user.id,
                    content_quality=2,
                    instructor_skills=2,
                    purchase_worth=2,
                    support_quality=2,
                    rates=2,
                    description="Pending",
                    status=ReviewStatus.pending,
                ),
            ]
        )
        root = Comment(
            course_id=course.id, user_id=user.id, comment="Top", status=CommentStatus.open
        )
        db.add(root)
        await db.flush()
        db.add(
            Comment(
                course_id=course.id,
                user_id=user.id,
                comment="Reply",
                reply_id=root.id,
                status=CommentStatus.new,
            )
        )
        await db.commit()
        return course.slug


async def test_detail_embeds_active_reviews_and_rating(client: AsyncClient):
    slug = await _seed()
    r = await client.get(f"/api/v1/courses/{slug}")
    assert r.status_code == 200
    body = r.json()
    # only the active review counts
    assert body["reviews_count"] == 1
    assert body["rate"] == 4.0
    assert len(body["reviews"]) == 1
    assert body["reviews"][0]["description"] == "Great"
    assert body["reviews"][0]["user"]["full_name"] == "Reviewer"
    assert body["rate_type"]["instructor_skills"] == 5.0


async def test_detail_embeds_comment_tree(client: AsyncClient):
    slug = await _seed()
    r = await client.get(f"/api/v1/courses/{slug}")
    comments = r.json()["comments"]
    assert len(comments) == 1  # one top-level
    assert comments[0]["comment"] == "Top"
    assert len(comments[0]["replies"]) == 1
    assert comments[0]["replies"][0]["comment"] == "Reply"


async def test_detail_no_reviews_zero_rate(client: AsyncClient):
    async with AsyncSessionLocal() as db:
        db.add(
            Course(
                title="Empty",
                slug="empty",
                type=CourseType.course,
                status=CourseStatus.active,
                price=0,
            )
        )
        await db.commit()
    r = await client.get("/api/v1/courses/empty")
    assert r.json()["rate"] == 0
    assert r.json()["reviews_count"] == 0
    assert r.json()["comments"] == []

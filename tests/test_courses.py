from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.category import Category
from app.models.course import Course, CourseStatus, CourseType
from tests.conftest import register_verified_user


async def _seed_course(
    *,
    title: str = "Python 101",
    slug: str = "python-101",
    status: CourseStatus = CourseStatus.active,
    private: bool = False,
    category_id: int | None = None,
    teacher_id: int | None = None,
    price: float = 100,
) -> int:
    async with AsyncSessionLocal() as db:
        course = Course(
            title=title,
            slug=slug,
            type=CourseType.course,
            status=status,
            private=private,
            category_id=category_id,
            teacher_id=teacher_id,
            price=price,
            description="Learn Python",
            support=True,
        )
        db.add(course)
        await db.commit()
        return course.id


async def test_list_courses_brief(client: AsyncClient):
    async with AsyncSessionLocal() as db:
        cat = Category(title="Programming", slug="prog", order=1)
        db.add(cat)
        await db.commit()
        category_id = cat.id

    _, teacher_id = await register_verified_user(client, email="teacher@aiacademy.tj")
    await _seed_course(category_id=category_id, teacher_id=teacher_id)
    await _seed_course(title="Draft", slug="draft", status=CourseStatus.is_draft)
    await _seed_course(title="Secret", slug="secret", private=True)

    r = await client.get("/api/v1/courses")
    assert r.status_code == 200
    body = r.json()
    # only the active, non-private course is listed
    assert [c["slug"] for c in body] == ["python-101"]
    course = body[0]
    assert course["category"] == "Programming"
    assert course["price"] == 100.0
    assert course["price_string"] == "100"
    assert course["teacher"]["id"] == teacher_id
    assert course["teacher"]["full_name"] == "Test User"
    # brief stays brief — no detail-only keys
    assert "chapters" not in course


async def test_course_detail(client: AsyncClient):
    await _seed_course()
    r = await client.get("/api/v1/courses/python-101")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "python-101"
    assert body["description"] == "Learn Python"
    assert body["support"] is True
    # later-phase relations present but stubbed (stable FE contract)
    assert body["chapters"] == []
    assert body["reviews"] == []
    assert body["quizzes_count"] == 0
    assert body["rate_type"]["content_quality"] == 0


async def test_course_detail_not_found(client: AsyncClient):
    r = await client.get("/api/v1/courses/nope")
    assert r.status_code == 404


async def test_private_course_hidden_from_detail(client: AsyncClient):
    await _seed_course(slug="secret", private=True)
    r = await client.get("/api/v1/courses/secret")
    assert r.status_code == 404


async def test_categories_webinars_count(client: AsyncClient):
    async with AsyncSessionLocal() as db:
        prog = Category(title="Programming", slug="prog", order=1)
        db.add(prog)
        await db.flush()
        py = Category(title="Python", parent_id=prog.id, order=1)
        db.add(py)
        await db.commit()
        py_id = py.id

    await _seed_course(slug="a", category_id=py_id)
    await _seed_course(slug="b", category_id=py_id, status=CourseStatus.is_draft)

    r = await client.get("/api/v1/categories")
    assert r.status_code == 200
    top = r.json()["categories"][0]
    sub = top["sub_categories"][0]
    # legacy webinars_count ignores status; top sums its subcategories
    assert sub["webinars_count"] == 2
    assert top["webinars_count"] == 2

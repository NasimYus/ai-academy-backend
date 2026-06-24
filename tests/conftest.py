import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.database import AsyncSessionLocal, Base, engine
from app.main import app
from app.models.role import Role

# Tables truncated before each test (roles re-seeded). Run against a throwaway
# database (CI uses an ephemeral Postgres; locally point DATABASE_URL at *_test).
_DATA_TABLES = (
    "verifications",
    "password_resets",
    "payment_channels",
    "order_items",
    "orders",
    "discount_users",
    "discount_categories",
    "discount_courses",
    "discounts",
    "cart",
    "course_forum_answers",
    "course_forums",
    "course_noticeboards",
    "course_personal_notes",
    "certificates",
    "assignment_history_messages",
    "assignment_history",
    "assignments",
    "course_learning",
    "quizzes_results",
    "quizzes_questions_answers",
    "quizzes_questions",
    "quizzes",
    "enrollments",
    "featured_courses",
    "comments",
    "course_reviews",
    "course_files",
    "text_lessons",
    "course_sessions",
    "chapters",
    "trend_categories",
    "categories",
    "courses",
    "users",
    "roles",
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_db():
    async with AsyncSessionLocal() as db:
        await db.execute(text(f"TRUNCATE {', '.join(_DATA_TABLES)} RESTART IDENTITY CASCADE"))
        db.add_all(
            [
                Role(id=1, name="user", caption="User", is_admin=False),
                Role(id=2, name="admin", caption="Admin", is_admin=True),
                Role(id=3, name="organization", caption="Organization", is_admin=False),
                Role(id=4, name="teacher", caption="Teacher", is_admin=False),
            ]
        )
        await db.commit()
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register_verified_user(
    client: AsyncClient, email: str = "user@aiacademy.tj", password: str = "secret12345"
) -> tuple[str, int]:
    """Run the 3-step registration and return (access_token, user_id)."""
    r = await client.post(
        "/api/v1/auth/register/step/1",
        json={"email": email, "password": password, "password_confirmation": password},
    )
    body = r.json()
    await client.post(
        "/api/v1/auth/register/step/2", json={"user_id": body["user_id"], "code": body["code"]}
    )
    r = await client.post(
        "/api/v1/auth/register/step/3",
        json={"user_id": body["user_id"], "full_name": "Test User"},
    )
    data = r.json()
    return data["access_token"], data["user_id"]

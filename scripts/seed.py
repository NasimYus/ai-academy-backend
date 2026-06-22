"""Seed minimal dev data: one admin, one teacher, a few published courses.

Run with:  uv run python -m scripts.seed
Idempotent — safe to run repeatedly.
"""
import asyncio

from app.core.database import AsyncSessionLocal
from app.models.course import Course, CourseStatus
from app.models.user import UserRole
from app.repositories import courses as courses_repo
from app.repositories import users as users_repo


async def main() -> None:
    async with AsyncSessionLocal() as db:
        admin = await users_repo.get_by_email(db, "admin@aiacademy.tj")
        if admin is None:
            admin = await users_repo.create(
                db,
                email="admin@aiacademy.tj",
                password="admin12345",
                full_name="AI Academy Admin",
                role=UserRole.admin,
                is_verified=True,
            )
            print(f"created admin: {admin.email} / admin12345")

        teacher = await users_repo.get_by_email(db, "teacher@aiacademy.tj")
        if teacher is None:
            teacher = await users_repo.create(
                db,
                email="teacher@aiacademy.tj",
                password="teacher12345",
                full_name="Demo Teacher",
                role=UserRole.teacher,
                is_verified=True,
            )
            print(f"created teacher: {teacher.email} / teacher12345")

        samples = [
            ("Introduction to AI", "introduction-to-ai", "Basics of artificial intelligence.", 0),
            ("Python for Data Science", "python-for-data-science", "Hands-on Python & data.", 199),
            ("Machine Learning 101", "machine-learning-101", "Core ML concepts and models.", 299),
        ]
        for title, slug, desc, price in samples:
            if await courses_repo.get_by_slug(db, slug) is None:
                db.add(
                    Course(
                        title=title,
                        slug=slug,
                        description=desc,
                        price=price,
                        status=CourseStatus.published,
                        teacher_id=teacher.id,
                    )
                )
                print(f"created course: {slug}")
        await db.commit()
    print("seed done")


if __name__ == "__main__":
    asyncio.run(main())

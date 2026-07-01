"""Seed minimal dev data: one admin, one teacher, a few active courses.

Run with:  uv run python -m scripts.seed
Idempotent — safe to run repeatedly.
"""

import asyncio

from app.core.database import AsyncSessionLocal
from app.models.category import Category
from app.models.community_forum import ForumCategory
from app.models.course import Course, CourseStatus, CourseType
from app.models.role import Role
from app.repositories import categories as categories_repo
from app.repositories import community_forum as forum_repo
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
                role_name=Role.ADMIN,
                verified=True,
            )
            print(f"created admin: {admin.email} / admin12345")

        teacher = await users_repo.get_by_email(db, "teacher@aiacademy.tj")
        if teacher is None:
            teacher = await users_repo.create(
                db,
                email="teacher@aiacademy.tj",
                password="teacher12345",
                full_name="Demo Teacher",
                role_name=Role.TEACHER,
                verified=True,
            )
            print(f"created teacher: {teacher.email} / teacher12345")

        existing_cats = {c.title for c in await categories_repo.list_all(db)}
        for order, title in enumerate(
            [
                "Искусственный интеллект",
                "Программирование",
                "Data Science",
                "Дизайн",
                "Бизнес и маркетинг",
            ]
        ):
            if title not in existing_cats:
                db.add(
                    Category(
                        title=title,
                        slug=await categories_repo.unique_slug(db, title),
                        order=order,
                        enable=True,
                    )
                )
                print(f"created category: {title}")
        await db.commit()

        existing_forums = {
            f.title for f, _ in await forum_repo.list_categories(db)
        }
        for order, (title, desc) in enumerate(
            [
                ("Общие вопросы", "Обсуждаем всё об обучении и платформе."),
                ("Помощь по курсам", "Вопросы по материалам и заданиям."),
                ("Карьера в AI", "Резюме, вакансии, развитие."),
            ]
        ):
            if title not in existing_forums:
                db.add(
                    ForumCategory(
                        title=title,
                        description=desc,
                        slug=await forum_repo.unique_category_slug(db, title),
                        order=order,
                    )
                )
                print(f"created forum category: {title}")
        await db.commit()

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
                        type=CourseType.course,
                        status=CourseStatus.active,
                        teacher_id=teacher.id,
                        creator_id=teacher.id,
                    )
                )
                print(f"created course: {slug}")
        await db.commit()
    print("seed done")


if __name__ == "__main__":
    asyncio.run(main())

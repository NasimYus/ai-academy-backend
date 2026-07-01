from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    admin_categories,
    admin_courses,
    admin_payments,
    admin_reviews,
    admin_users,
    assignments,
    auth,
    become_instructor,
    blog,
    bundles,
    cart,
    categories,
    certificates,
    comments,
    contact,
    courses,
    currencies,
    dashboard,
    enrollment,
    events_calendar,
    favorites,
    featured,
    financial,
    follows,
    forums,
    gifts,
    instructor,
    meetings,
    newsletter,
    noticeboards,
    notifications,
    orders,
    payments,
    personal_notes,
    products,
    profile,
    providers,
    quizzes,
    registration_packages,
    reviews,
    rewards,
    sales,
    search,
    subscriptions,
    support,
)
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(courses.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(contact.router, prefix="/api/v1")
app.include_router(currencies.router, prefix="/api/v1")
app.include_router(featured.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(enrollment.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(events_calendar.router, prefix="/api/v1")
app.include_router(comments.router, prefix="/api/v1")
app.include_router(financial.router, prefix="/api/v1")
app.include_router(become_instructor.router, prefix="/api/v1")
app.include_router(favorites.router, prefix="/api/v1")
app.include_router(follows.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(quizzes.router, prefix="/api/v1")
app.include_router(assignments.router, prefix="/api/v1")
app.include_router(certificates.router, prefix="/api/v1")
app.include_router(personal_notes.router, prefix="/api/v1")
app.include_router(noticeboards.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(newsletter.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(rewards.router, prefix="/api/v1")
app.include_router(sales.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(registration_packages.router, prefix="/api/v1")
app.include_router(instructor.router, prefix="/api/v1")
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(support.router, prefix="/api/v1")
app.include_router(blog.router, prefix="/api/v1")
app.include_router(bundles.router, prefix="/api/v1")
app.include_router(forums.router, prefix="/api/v1")
app.include_router(gifts.router, prefix="/api/v1")
app.include_router(cart.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(admin_payments.router, prefix="/api/v1")
app.include_router(admin_courses.router, prefix="/api/v1")
app.include_router(admin_categories.router, prefix="/api/v1")
app.include_router(admin_users.router, prefix="/api/v1")
app.include_router(admin_reviews.router, prefix="/api/v1")

# Serve uploaded media from local storage (F.1).
Path(settings.media_root).mkdir(parents=True, exist_ok=True)
app.mount(settings.media_url, StaticFiles(directory=settings.media_root), name="media")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}

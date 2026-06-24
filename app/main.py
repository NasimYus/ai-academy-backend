from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    assignments,
    auth,
    cart,
    categories,
    certificates,
    courses,
    currencies,
    enrollment,
    featured,
    forums,
    noticeboards,
    orders,
    payments,
    personal_notes,
    profile,
    providers,
    quizzes,
    search,
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
app.include_router(currencies.router, prefix="/api/v1")
app.include_router(featured.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(enrollment.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(quizzes.router, prefix="/api/v1")
app.include_router(assignments.router, prefix="/api/v1")
app.include_router(certificates.router, prefix="/api/v1")
app.include_router(personal_notes.router, prefix="/api/v1")
app.include_router(noticeboards.router, prefix="/api/v1")
app.include_router(forums.router, prefix="/api/v1")
app.include_router(cart.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")

# Serve uploaded media from local storage (F.1).
Path(settings.media_root).mkdir(parents=True, exist_ok=True)
app.mount(settings.media_url, StaticFiles(directory=settings.media_root), name="media")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}

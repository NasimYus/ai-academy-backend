# AI Academy — Backend (FastAPI)

REST API for the AI Academy LMS. Async FastAPI + SQLAlchemy 2.0 + PostgreSQL.
Serves a separate TanStack Start SPA frontend (`ai-academy-frontend`).

## Stack
- **FastAPI** (async) — API + auto OpenAPI/Swagger
- **SQLAlchemy 2.0** (async, asyncpg) + **Alembic** migrations
- **PostgreSQL 16**
- **PyJWT** + **passlib[bcrypt]** — JWT auth, hashed passwords
- **uv** — dependency management

## Layout
```
app/
  core/         config, database (async engine/session), security (JWT, hashing)
  models/       SQLAlchemy models (User, Course, ...)
  schemas/      Pydantic v2 request/response models
  repositories/ DB access layer (keeps routes thin)
  api/
    deps.py     get_db, get_current_user, require_role
    routes/     auth, courses, ...
  main.py       FastAPI app + CORS + routers
migrations/     Alembic
scripts/seed.py dev seed data
```

## Quickstart (local)
```bash
# 1. install deps
uv sync

# 2. env
cp .env.example .env

# 3. database — either docker:
docker compose up -d db
#    ...or a local Postgres with db/user "aiacademy"

# 4. migrate + seed
uv run alembic upgrade head
uv run python -m scripts.seed

# 5. run
uv run uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json  ← frontend generates its client + Zod from this
- Health: http://localhost:8000/health

## Auth flow
- `POST /api/v1/auth/register` → creates user, returns a verification token (dev only; e-mailed in prod)
- `POST /api/v1/auth/verify?token=...` → marks e-mail verified
- `POST /api/v1/auth/login` → `{ access_token }` (JWT bearer)
- `GET  /api/v1/auth/me` → current user

## Migrations
```bash
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

## Dev seed accounts
- admin@aiacademy.tj / admin12345
- teacher@aiacademy.tj / teacher12345

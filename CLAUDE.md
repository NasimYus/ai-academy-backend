# CLAUDE.md — AI Academy Backend

FastAPI backend для LMS. Это переписывание легаси Laravel-проекта (`../ai-academy`)
на новый стек. **Главный принцип: 1:1 паритет бизнес-логики с легаси — ни больше,
ни меньше.** Меняется только стек/структура, не поведение.

## Стек
FastAPI · async SQLAlchemy 2.0 (asyncpg) · Alembic · Pydantic v2 / pydantic-settings ·
JWT (pyjwt) · bcrypt · **uv** (пакеты). Python ≥ 3.11. БД — PostgreSQL.

## Команды
```bash
uv sync                                   # установка зависимостей (вкл. dev)
docker compose up -d db                   # Postgres локально (или свой кластер)
uv run alembic upgrade head               # применить миграции
uv run alembic revision -m "msg"          # новая миграция (обычно правим вручную)
uv run uvicorn app.main:app --reload      # дев-сервер :8000
uv run pytest -q                          # тесты (нужен Postgres, см. ниже)
uv run ruff check && uv run ruff format   # линт + формат
```
Env: дефолты в `app/core/config.py` (БД `postgresql+asyncpg://aiacademy:aiacademy@localhost:5432/aiacademy`). Переопределяется через `.env` / переменные окружения.

## Архитектура (слои)
```
app/
  core/         config, database (engine/Base/get_db), security (jwt/bcrypt)
  models/       SQLAlchemy-модели (+ __init__ регистрирует их для Alembic)
  schemas/      Pydantic (request/response); common.py: ErrorResponse + error_responses()
  repositories/ доступ к данным (чистые функции над AsyncSession)
  services/     оркестрация (verification, storage)
  api/
    deps.py     DbSession, CurrentUser, require_role/require_level
    routes/     роутеры (подключаются в main.py с префиксом /api/v1)
  main.py       приложение, CORS, монтирование /media
migrations/     Alembic (env.py async; offline отключён)
tests/          pytest-asyncio
```
Поток среза: **model → migration → schema → repository → route**. Логику-оркестрацию
кладём в `services/`. Каждый раскрываемый эндпоинт документирует ошибки через
`responses=error_responses(...)` (иначе openapi-fetch на фронте типизирует `error` как never).

## Конвенции
- **Паритет легаси**: перед реализацией читаем соответствующий контроллер/модель в `../ai-academy`.
- Идиоматичные PG-типы вместо MySQL-причуд (timestamptz вместо epoch-int и т.п.).
- **Гейт-заглушки**: фичи поздних фаз (rewards/affiliate/newsletter/firebase/zoom) — настройко-гейтнутые no-op на чистой БД (как легаси). Помечены `NOTE(Phase N)`.
- Статусы 422 — `status.HTTP_422_UNPROCESSABLE_CONTENT` (не deprecated `_ENTITY`).
- ruff: line-length 100, `select=[E,F,I,UP,B]`, `ignore=[UP042]` (оставляем `str, Enum`).
- В `debug` режиме коды верификации/reset-токены отдаются в ответе (для тестов без почты).
- `media/` (загрузки) в `.gitignore`.

## Тесты
- `tests/conftest.py`: создаёт схему (`Base.metadata.create_all`), **truncate + сид ролей перед каждым тестом**, фикстуры `client` (httpx ASGI) и `register_verified_user`.
- Нужен **отдельный** Postgres (CI поднимает сервис; локально — `aiacademy_test`):
  `DATABASE_URL=postgresql+asyncpg://aiacademy:aiacademy@localhost:5432/aiacademy_test uv run pytest -q`
- `pyproject.toml`: `asyncio_mode=auto`, loop scope = session (иначе asyncpg «different loop»).
- Покрытие отмечаем в `CHANGELOG.md` пометкой 🧪.

## Процесс и документы
- **Рабочий цикл**: перенёс модуль на беке → тот же на фронте (`../ai-academy-frontend`) → тест → отметка в чеклисте → дальше.
- Roadmap и принципы: **`MIGRATION_PLAN.md`**.
- Прогресс (что готово / покрыто тестами / осталось): **`CHANGELOG.md`** — обновлять каждый срез.
- После изменения API фронт регенерит типы (`bun run gen:api`).
- Ветка разработки и пуш — `main` (работаем напрямую).
- CI: `.github/workflows/ci.yml` (postgres service → ruff → pytest) на каждый push.

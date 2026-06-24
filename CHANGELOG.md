# Changelog — AI Academy Backend

Прогресс переписывания LMS с Laravel на FastAPI. Полный roadmap и принципы —
см. `MIGRATION_PLAN.md`. Этот файл — живой трекер: отмечаем по мере готовности.

**Легенда:** ✅ готово · 🧪 покрыто тестами · 🟡 частично · ⬜ todo
Тесты: `pytest` (async, на Postgres) — `uv run pytest`. CI: GitHub Actions `on: push`.

---

## Phase 0 — Фундамент

- ✅ FastAPI + async SQLAlchemy + Alembic + JWT; слои models/schemas/repositories/api/core
- ✅ JWT (`create_token`/`decode_token`), bcrypt (`hash_password`/`verify_password`)
- ✅ Честные error-ответы в OpenAPI (`ErrorResponse` + `error_responses()`)
- ✅ 🧪 Тестовая инфраструктура (`tests/conftest.py`: схема + truncate + сид ролей) и CI (postgres service + ruff + pytest)

## Phase 1 — Auth & профиль

- ✅ 🧪 **1.0** `roles` (+сид user/admin/organization/teacher) и `users` (64 колонки, паритет легаси); Alembic
- ✅ 🧪 **1.1** Регистрация 3 шага + верификация по коду (`/auth/register/step/{1,2,3}`, `/auth/verification`, `verifications` таблица)
- ✅ 🧪 **1.2** Login (email/mobile, бан+авторазбан, `not_verified`, device-limit, `logged_count`, `profile_completion`) + `/auth/logout`
- ✅ 🧪 **1.3** Forgot/reset password (`/auth/forget-password`, `/auth/reset-password/{token}`, `password_resets`)
- ✅ 🧪 **1.4** Профиль `/panel/profile-setting` (get/update/password/images) + **F.1** локальное хранилище `/media`
- ✅ 🧪 **1.5** Гварды `require_role`/`require_level` (иерархия LevelAccess)
- ✅ 🧪 **1.6** OAuth callbacks `/auth/{google,facebook}/callback`
- ⬜ admin-CRUD для users/ролей (наращиваем постепенно)

## Phase 2 — Каталог (public)

- ✅ 🧪 **2.1** Categories + trend (`/categories`, `/trend-categories`; модели `Category`/`TrendCategory`)
- ✅ 🧪 **2.2** Course detail: `Course` расширен под `webinars`-паритет (миграция `f6a7b8c9d0e1`), `GET /courses/{slug}` → `CourseDetail` (legacy brief+details; поздние секции — стабы), list → `brief`, `webinars_count` оживлён. Relationship'ы `lazy="raise"` + `selectinload` (greenlet-safe)
- ✅ 🧪 **2.3** Filters на `GET /courses` (cat/free/type/upcoming/downloadable/reward/sort — column-backed; discount/filter_option/moreOptions → их фазы) + global `GET /search` (webinars/users/teachers/organizations, min 3 симв.); пресентер `course_presenter`
- ✅ 🧪 **2.4** Featured (`GET /featured-courses`; `FeaturedCourse` модель/миграция; page home/home_categories + status publish → brief активных публичных курсов)
- ✅ 🧪 **2.5** Instructors/providers + публичный профиль (`/providers/{instructors,organizations,consultations}`, `/users/{id}/profile`; active+non-banned; consultations пусто до Phase 7; cashback→null)
- ✅ 🧪 **2.6** Reviews & comments (чтение): модели `CourseReview`/`Comment`+миграция; в `GET /courses/{slug}` встроены active-отзывы, агрегаты (rate/reviews_count/rate_type) и дерево комментариев

## Phase 3 — Обучение (enrolled)

- ✅ 🧪 **3.1** Enrollment + проверка доступа: `Enrollment` модель/миграция; `POST /panel/courses/{id}/free` (free-enroll); `access.has_course_access` (owner|enrolled; paid→Phase 4); optional-auth → `auth`/`auth_has_bought` в детали курса
- ✅ 🧪 **3.2** Chapters + lesson items: модели `Chapter`/`File`/`TextLesson`/`CourseSession`+миграция; `GET /courses/{slug}/content` (главы+items, гейтинг по accessibility/доступу — locked прячет file/content/link)
- ✅ 🧪 **3.3** Прогресс обучения: модель/миграция `CourseLearning` (полиморфно по file/text_lesson/session, denorm `course_id`); `POST /courses/{id}/learning` (toggle, требует доступа → 403 `not_purchased`, валидирует принадлежность item курсу); флаг `completed` в `/content` для авторизованного; `course_id` в ответе content
- ✅ 🧪 **3.4** Quizzes (student-flow): модели/миграция `Quiz`/`QuizQuestion`/`QuizQuestionAnswer`/`QuizResult` (results=JSONB); `GET /quizzes/{id}` (show + auth-поля), `GET /courses/{id}/quizzes`, `GET /quizzes/{id}/start` (гейт take_status → 403 not_purchased/passed/max_attempt), `POST /quizzes/{id}/store-result` (грейдинг: multiple/negative_grade, descriptive→waiting), `GET /quizzes/{id}/result`, `GET /quizzes/results/{id}/status`. Отложено: rewards/certificate/notifications/instructor-review
- ✅ 🧪 **3.5** Assignments (student-flow): модели/миграция `Assignment`/`AssignmentHistory`/`AssignmentHistoryMessage` (`a3b4c5d6e7f8`); `GET /assignments/{id}` + `GET /courses/{id}/assignments`, `GET /panel/my_assignments[/{id}]`, `GET|POST /assignments/{id}/messages` (multipart submit+attachment, history создаётся при первом сообщении, гейт deadline/attempts → 401, access-gate → 403, not_submitted→pending). Отложено: грейдинг/review инструктора, attachments-аплоады инструктора (Phase 6)
- ✅ 🧪 **3.6** Certificates (achievements + PDF + validation): модель/миграция `Certificate` (`b4c5d6e7f8a9`); выдача при сдаче quiz с флагом `certificate` (вшито в store-result); `GET /panel/certificates/achievements` (пройденные quiz + сертификат), `GET /panel/quizzes/results/{id}/show` (синхронный рендер PDF через `fpdf2`, кэш на диске → FileResponse), публичная `GET /certificate_validation?certificate_id=`. Отложено: шаблоны (CertificateTemplate) + позиционирование, Unicode-шрифт для кириллицы (latin-1 fallback, NOTE F.6) — Phase 6
- ✅ 🧪 **3.7** Personal notes: модель/миграция `CoursePersonalNote` (target_type enum + target_id, уник по user+course+target); `GET /personal-notes?type=&item=` (404 not_found), `POST /personal-notes` (multipart upsert + attachment через storage F.1), `DELETE /personal-notes/delete/{id}` (scoped к владельцу — легаси оставлял без скоупа). NOTE: `course_notes_status`-гейт отложён (нет settings-инфры)
- ✅ 🧪 **3.8** Noticeboards: модель/миграция `CourseNoticeboard` (color enum); `GET /courses/{id}/noticeboards` (newest-first, color→icon как в легаси, creator brief). NOTE: seen-трекинг (`course_noticeboard_status`) опущен — API его не использует
- ⬜ **3.9** Forums (Q&A)

## Phase 4 — Коммерция

- ⬜ **4.1** Cart · **4.2** Coupons/discounts · **4.3** Checkout/Orders
- ⬜ **4.4** Payments (абстракция шлюзов + verify/webhook) · **4.5** Покупка→enrollment · **4.6** Purchases

## Сквозные задачи (foundation)

- ✅ **F.1** Файловое хранилище (локальный диск, `/media`; S3 — позже)
- ⬜ **F.2** Фоновые задачи (arq/Celery) — email/FCM/PDF
- ⬜ **F.3** Email/SMS отправка (verification, reset, чеки) — сейчас заглушки
- ⬜ **F.4** i18n контента (translatable: категории/курсы/…)
- ⬜ **F.5** Мультивалюта (`MultiCurrency`)

## Backlog (после MVP)

- ⬜ **Phase 5** Вовлечение: favorites, follow, notifications(+FCM), support, blog, newsletter, rewards
- ⬜ **Phase 6** Инструктор: создание курсов/квизов, грейдинг, bundles, store, статистика
- ⬜ **Phase 7** Live & advanced: meetings/reservations, Agora/Zoom/BBB, subscriptions, gifts
- ⬜ **Admin**: панель (наращиваем по фазам)

## Гейт-заглушки (включаются в своих фазах)

- 🟡 reward/affiliate/registration-bonus/form-fields в регистрации (Phase 5)
- 🟡 UserFirebaseSessions, история входов, JWT-denylist в login/logout (Phase 5 / infra)
- 🟡 Newsletter+reward, UserMeta (gender/age), Zoom API в профиле (Phase 5)
- 🟡 верификация provider-токена в OAuth (hardening)

# AI Academy — план переноса (Laravel → FastAPI + TanStack SPA)

Канонический roadmap переписывания легаси-LMS (`ai-academy`, Laravel) на новый
стек: **backend** `ai-academy-backend` (FastAPI + async SQLAlchemy + Alembic +
JWT), **frontend** `ai-academy-frontend` (TanStack Start SPA, FSD).

## Как работаем (вертикальный срез)

> **Главный принцип: 1:1 паритет логики с легаси — ни больше, ни меньше.**
> Источник истины — соответствующий контроллер/модель в `ai-academy` (Laravel).
> Перед каждым срезом читаем легаси-код и воспроизводим поведение точь-в-точь.
> Меняется только *стек* (FastAPI/SPA/FSD) и *структура* — **не бизнес-логика**.
> Никаких добавлений «от себя» (refresh-токены, новые поля, лишние абстракции).

Для каждого модуля идём строго по циклу и отмечаем статус:

1. **BE** — модель + Alembic-миграция + repository + endpoints + schemas.
2. **API** — типы для фронта: `bun run gen:api` (или дамп `app.openapi()` →
   `openapi-typescript`).
3. **FE** — FSD-слайс(ы): `entities/*` → `features/*` → `pages/*`, через
   публичный API (`index.ts`). Проверка: `bun run lint && lint:fsd && tsc && build`.
4. **Test** — smoke/ручная проверка сквозного сценария.
5. **Admin** — CRUD для сущностей этой фазы (наращиваем постепенно).
6. Отметить `[x]` и двигаться дальше.

Легенда: `[ ]` todo · `[~]` в работе · `[x]` готово.
Термины легаси: **webinar = course**, chapter/chapter-item = глава/урок.

---

## Phase 0 — Фундамент ✅

- [x] BE: FastAPI + async SQLAlchemy + Alembic + JWT; слои models/schemas/repositories/api/core
- [x] BE: модели `User`, `Course`; auth (register/login/me/verify), courses (list/get-by-slug)
- [x] BE: честные error-ответы в OpenAPI (`ErrorResponse`)
- [x] FE: TanStack Start SPA, **FSD** + steiger, TanStack Query, Zustand-сессия, typed openapi-fetch
- [x] FE: брендинг (токены, шрифты, header), login/courses страницы
- [x] Тесты + CI: BE pytest (auth/profile/categories/guards) на Postgres; FE vitest
      (store/guards/схемы); GitHub Actions `on: push` в обоих репо

---

## Phase 1 — Auth & профиль

- [x] **1.0 User-модель под паритет + roles + миграция**
  - [x] BE: `roles` (+сид) и `users` (64 колонки, паритет легаси), Alembic-миграция применена
  - [x] BE: реконсиляция schemas/repo/deps/routes (`status`/`verified`/`role_name`/`password`)
  - [x] API: типы перегенерированы (`UserRead`)  [x] FE: сборка/линт/типы зелёные
  - [x] test: smoke register→login→me против реальной БД
- [x] **1.1 Register (3 шага) + Verification по коду** — паритет легаси
  - [x] BE: `verifications` таблица/модель/миграция; `check_confirmed`/`confirm_code`;
        `/register/step/{1,2,3}` + `/verification`; settings-гейты (register_method,
        disable_verification, users_affiliate); satellite (reward/affiliate/bonus/form-fields) — заглушки
  - [x] API: типы перегенерированы  [x] FE: `features/auth/register` (3-шаговая форма) + `pages/register` + route + ссылки login↔register
  - [x] test: smoke step1→2→3→login→me + wrong-code/already-registered/short-pw
  - [ ] admin (управление верификацией/настройками)
- [x] **1.2 Login (email/mobile, ban, device-limit) + logout** — паритет легаси
  - [x] BE: вход по email/mobile, бан с авторазбаном, неактивный→`not_verified`(+код),
        device-limit (settings-гейт), `logged_count`, `profile_completion`; `/logout` (logged_count--)
  - [x] BE-заглушки: UserFirebaseSessions, история входов, JWT-denylist (Phase 5 / infra)
  - [x] API типы перегенерированы  [x] FE: login шлёт `username`; `features/auth/logout` (server logout→очистка сессии), Header
  - [x] test: login active/wrong-pw/pending(not_verified) + logout
- [x] **1.3 Forgot / reset password** — паритет легаси
  - [x] BE: `password_resets` таблица/модель/миграция; `/forget-password`
        (email→токен / mobile→новый пароль) + `/reset-password/{token}`; доставка email/SMS — deferred (F.3), в debug токен/пароль в ответе
  - [x] API типы перегенерированы  [x] FE: `features/auth/reset-password` (forgot+reset формы), `pages/forgot-password` + `pages/reset-password` + routes, ссылка со входа
  - [x] test: forgot→reset→login, bad-token (benign), unknown-email 404, mismatch 422
  - _mobile-flow UI отложен (register_method=email); API-паритет есть_
- [x] **1.4 Профиль: get/update, смена пароля, загрузка изображений** — паритет легаси
  - [x] BE: `/panel/profile-setting` GET/PUT, `/password` (verify+новый токен), `/images` (avatar/identity/certificate); email/mobile uniqueness; level_of_training→битмаска; location→"lat,lng"
  - [x] BE-заглушки: Newsletter+reward, UserMeta (gender/age), Zoom API (Phase 5)
  - [x] FE: `features/profile` (ProfileForm/PasswordForm/AvatarForm) + `pages/profile` + guarded route + ссылка в Header
  - [x] test: get/update(bitmask,newsletter)/password(+wrong)/login-new-pwd/image-upload
  - [ ] admin (users)
- [x] **1.5 Роли и гварды доступа** — паритет легаси (Api\LevelAccess)
  - [x] BE: `require_role(*names)` + `require_level(level)` (иерархия user⊃teacher⊃organization), `LEVEL_ACCESS`-карта
  - [x] FE: `entities/session` guards `requireAuth`/`requireRole`; роуты courses/profile через `requireAuth`
  - [x] test: unit-проверка allow/deny по ролям/уровням
  - _requireRole пока не навешан на страницы (нет role-gated экранов до Phase 6) — инфраструктура готова_
- [x] **1.6 OAuth (Google/Facebook)** — паритет легаси (SocialiteController)
  - [x] BE: `POST /auth/{google,facebook}/callback` (trust posted {email,name,id}); find by provider_id|email → create(verified, password=null) или login+token; новый аккаунт без токена (legacy-квирк)
  - [x] FE: `features/auth/oauth` (api+hook+`OAuthButtons`, env-gated `VITE_GOOGLE_CLIENT_ID`/`VITE_FACEBOOK_APP_ID`) на login/register
  - [x] test: google new→registered / repeat→login+token / cross-provider by email / me
  - _активация требует provider SDK + client_id; верификация provider-токена на бэке — TODO (hardening)_

---

## Phase 2 — Каталог (public)

- [x] **2.1 Categories (+ trend categories)** — паритет легаси (CategoriesController)
  - [x] BE: `Category`+`TrendCategory` модели/миграция; `GET /categories` (top-level+подкатегории+color), `GET /trend-categories`
  - [x] FE: `entities/category` (queryOptions+типы), `CategoryNav` на странице курсов
  - [x] test: seed+smoke (2 категории, подкатегории, trend color)
  - _title i18n → F.4; webinars_count=0 до 2.2 (Course.category_id); admin позже_
- [x] **2.2 Course detail** (полные метаданные: инструктор, цена, статус, бейджи, что внутри) — паритет легаси (WebinarController@show)
  - [x] BE: `Course` расширен под `webinars`-паритет (тип/статус active/pending/is_draft/inactive, category_id, teacher, медиа, флаги; epoch→timestamptz); миграция `f6a7b8c9d0e1`; `GET /courses/{slug}` → `CourseDetail` (= legacy brief+details, поздне-фазовые секции — стабы `NOTE(Phase N)`); list отдаёт `brief`; `webinars_count` оживлён в `/categories`
  - [x] API: типы перегенерированы (`CourseRead`/`CourseDetail`/`CourseTeacher`)  [x] FE: `entities/course` (brief+detail query, обновлён `CourseCard`-ссылка) + `pages/course` + публичный роут `/course/$slug`
  - [x] test: list(active/draft/private)/detail/404/private-hidden + categories webinars_count; FE tsc/lint/steiger/vitest/build зелёные
  - [ ] admin (курсы)
  - _greenlet-фикс из HANDOFF §7.1 закрыт превентивно: relationship'ы `lazy="raise"` + `selectinload(teacher,category)` в repo_
- [x] **2.3 Search & filters** (категория, цена, тип, сортировка) — паритет легаси (handleFilters + SearchController)
  - [x] BE: фильтры на `GET /courses` (cat/free/type/upcoming/downloadable/reward/sort, column-backed); `GET /search` (webinars/users/teachers/organizations); `course_presenter`
  - [x] FE: `widgets/course-filters` (категория/тип/сортировка/бесплатные) на странице курсов; `coursesQueryOptions(filters)`
  - [x] test: list active/public-only, filter free/type/downloadable, sort, search (+too-short)
  - _discount/filter_option/moreOptions фильтры → свои фазы; global-search UI отложен (endpoint готов)_
- [x] **2.4 Featured courses** — паритет легаси (FeatureWebinarController)
  - [x] BE: `FeaturedCourse` модель/миграция (`a7b8c9d0e1f2`); `GET /featured-courses` (page home/home_categories + publish → brief активных публичных)
  - [x] FE: `featuredCoursesQueryOptions` + блок «Рекомендуемые» на странице курсов
  - [x] test: published-home only / pending+wrong-page excluded / empty
  - [ ] admin (управление витриной)
- [x] **2.5 Instructors / providers + публичный профиль** — паритет легаси (UserController)
  - [x] BE: `/providers/{instructors,organizations,consultations}` (active+non-banned, search/sort), `/users/{id}/profile` (+ их курсы); consultations пусто до Phase 7 (meetings); cashback→null
  - [x] FE: `entities/instructor` + `pages/instructors` (/instructors) + `pages/user` (/users/$userId) + nav в Header
  - [x] test: instructors (excl. banned/non-teacher), organizations, consultations empty, profile+courses, 404
- [x] **2.6 Reviews & comments (чтение)** — паритет легаси (webinar_reviews + comments)
  - [x] BE: модели `CourseReview`/`Comment` + миграция `b8c9d0e1f2a3`; `GET /courses/{slug}` встраивает active-отзывы, агрегаты (rate/reviews_count/rate_type) и дерево комментариев (reply_id)
  - [x] FE: рейтинг + секции «Отзывы»/«Комментарии» на странице курса; ссылка на профиль инструктора
  - [x] test: active-only отзывы + агрегат, дерево комментов, пустой курс
  - [ ] admin (модерация); запись отзывов/комментов (auth) — отдельно

---

## Phase 3 — Обучение (enrolled, ядро LMS)

- [x] **3.1 Enrollment + проверка доступа** — паритет легаси (checkUserHasBought + free-enroll)
  - [x] BE: `Enrollment` модель/миграция `c9d0e1f2a3b4`; `POST /panel/courses/{id}/free`; `services/access.has_course_access` (owner|enrolled; subscribe/installment/gift/bundle→Phase 4); `OptionalUser` dep; `auth`/`auth_has_bought` в `GET /courses/{slug}`
  - [x] FE: `features/course-enroll` + кнопки на детали курса (Записаться бесплатно / Вы записаны / Войдите)
  - [x] test: free-enroll grants access (+idempotent), paid rejected, requires auth, anon no access
  - [ ] BE `enrollments` + access-зависимость  [ ] FE гейтинг контента  [ ] test
- [x] **3.2 Chapters + lesson items** (file/text/session) — паритет легаси (WebinarController@content)
  - [x] BE: модели `Chapter`/`File`/`TextLesson`/`CourseSession` + миграция `d0e1f2a3b4c5` (direct chapter_id+order); `GET /courses/{slug}/content` с гейтингом (free | has_access; locked прячет file/content/link)
  - [x] FE: `pages/learn` (/learn/$slug) + `courseContentQueryOptions`; ссылка «Перейти к обучению»
  - [x] test: anon (free/ paid-locked+preview), enrolled (unlocked), 404
  - [ ] admin (CRUD контента) — Phase 6
- [x] **3.3 Прогресс обучения** (learning status toggle) — паритет легаси (WebinarController@learningStatus)
  - [x] BE `CourseLearning`+миграция, `POST /courses/{id}/learning`, `completed` в content  [x] FE отметки пройдено (`features/lesson-progress` + чекбоксы)  [x] test (toggle/unmark/access/404)
- [x] **3.4 Quizzes: прохождение + результаты** — паритет легаси (QuizzesController/QuizzesResultController, student-flow)
  - [x] BE `Quiz`/`QuizQuestion`/`QuizQuestionAnswer`/`QuizResult`+миграция; show/start/store-result/status/result + course-list; грейдинг (multiple/descriptive→waiting, negative_grade, max_attempt)  [x] FE `entities/quiz` + `features/take-quiz` (QuizRunner) + `pages/quiz`  [x] test  [ ] admin (CRUD, instructor-review) — Phase 6
  - NOTE: rewards (Phase 5), certificate issue (3.6), notifications (gated), instructor review/updateResult — отложено
- [~] **3.5 Assignments: список/сдача + сообщения** — паритет легаси (AssignmentController/AssignmentHistoryMessageController, student-flow)
  - [x] BE `Assignment`/`AssignmentHistory`/`AssignmentHistoryMessage`+миграция; show/course-list/my_assignments/messages(get+post); deadline+attempts гейт, access-gate, history-on-first-message  [ ] FE `features/submit-assignment`  [x] test  [ ] admin (грейдинг/review — Phase 6)
- [~] **3.6 Certificates** (achievements, validation, рендер/скачивание) — паритет легаси (CertificatesController/MakeCertificate, student-flow)
  - [x] BE `Certificate`+миграция; выдача при сдаче quiz; achievements/show(PDF через fpdf2)/validation; sync-генерация + кэш на диске  [ ] FE `pages/certificates`  [x] test  [ ] admin (шаблоны/позиционирование, Unicode-шрифт — Phase 6)
- [x] **3.7 Personal notes** — паритет легаси (CoursePersonalNotesController)
  - [x] BE `CoursePersonalNote`+миграция (`c5d6e7f8a9b0`), `GET/POST /personal-notes` (upsert по user+course+target), `DELETE /personal-notes/delete/{id}` (scoped to owner)  [x] FE `entities/note` + `features/personal-note` (NotePanel на items в `pages/learn`)  [x] test (BE: upsert/show/404/owner-scoped/bad-type)
  - NOTE: `course_notes_status` admin-гейт отложён (нет settings-инфры) — фича считается включённой; attachment-аплоад через storage(F.1)
- [x] **3.8 Noticeboards** — паритет легаси (CourseNoticeboardController@index)
  - [x] BE `CourseNoticeboard`+миграция (`d6e7f8a9b0c1`), `GET /courses/{id}/noticeboards` (color→icon, creator brief)  [x] FE `entities/noticeboard` + секция объявлений в `pages/learn`  [x] test (BE: list newest-first/icon/creator, auth, 404)  [ ] admin (CRUD) — Phase 6
  - NOTE: `course_noticeboard_status` (seen-трекинг) не используется API (seen закомментирован в легаси) — опущено
- [ ] **3.9 Forums (Q&A: threads, answers, pin, resolve)**
  - [ ] BE  [ ] FE `pages/course-forum`  [ ] test

---

## Phase 4 — Коммерция

- [ ] **4.1 Cart** (add / list / remove)
  - [ ] BE `Cart`  [ ] FE `entities/cart` + `pages/cart`  [ ] test
- [ ] **4.2 Coupons / discounts** (валидация)
  - [ ] BE `Discount` + validate  [ ] FE применение купона  [ ] test  [ ] admin
- [ ] **4.3 Checkout + Orders + OrderItems**
  - [ ] BE `Order`, `OrderItem`  [ ] FE `features/checkout`  [ ] test  [ ] admin
- [ ] **4.4 Payments — абстракция шлюзов** + 1–2 шлюза (выбрать под рынок TJ) + verify/webhook
  - [ ] BE gateway-интерфейс + реализация  [ ] FE redirect/return flow  [ ] test (sandbox)
- [ ] **4.5 Покупка → enrollment** (после успешной оплаты выдать доступ)
  - [ ] BE связка payment→enrollment  [ ] FE «мои курсы» после оплаты  [ ] test
- [ ] **4.6 Purchases (мои курсы)**
  - [ ] BE  [ ] FE `pages/my-courses`  [ ] test

> **🎯 Конец MVP.** Сквозной сценарий: регистрация → каталог → курс → оплата →
> обучение → сертификат. Инструктор-контент до Phase 6 заводим через
> seeds/админку.

---

## Сквозные задачи (foundation — подключать по мере необходимости)

- [x] **F.1 Файловое хранилище** — локальное disk-хранилище (`app/services/storage.py`),
      статика на `/media`; S3-совместимый бэкенд можно подменить за тем же интерфейсом позже
- [ ] **F.2 Фоновые задачи** (arq/Celery) — email, FCM, генерация PDF (нужно к 1.2 / 3.6)
- [ ] **F.3 Email-отправка** (verification, reset, чеки)
- [ ] **F.4 i18n контента** — воспроизвести translatable (мультиязык) как в легаси
- [ ] **F.5 Мультивалюта** — воспроизвести `MultiCurrency` как в легаси
- [ ] **F.6 i18n UI** на фронте (если нужен таджикский/русский/английский переключатель)

---

## Backlog (Phases 5–7 — детализируем после MVP)

- **Phase 5 — Вовлечение**: favorites, follow, notifications (+FCM), support-тикеты, blog, newsletter, rewards/баллы.
- **Phase 6 — Инструктор**: create/edit course (storeAll), chapters/lessons CRUD, quizzes CRUD, assignment grading, bundles, store/products, statistics, registration-packages.
- **Phase 7 — Live & advanced**: meetings/reservations (консультации), live-сессии (Agora/Zoom/BBB), subscriptions, bundle purchase, gifts.
- **Admin**: наращиваем постепенно — на каждой фазе добавляем CRUD для её сущностей (отмечено `admin` в чекбоксах выше).

---

## Решения по скоупу (= как в легаси)

Все «открытые вопросы» сняты главным принципом — делаем как в легаси:

- **Токены**: как у легаси (Laravel Sanctum — bearer-токен, logout ревокает).
  Refresh-токенов нет → не добавляем. _(текущий JWT-скелет привести к этому поведению)_
- **Регистрация**: многошаговая `register/step/{step}` — как в легаси.
- **Verification**: по коду (`VerificationController@confirmCode`) — как в легаси.
- **OAuth Google/Facebook**: есть в легаси → переносим (Socialite-аналог).
- **Платёжные шлюзы**: те, что реально включены в легаси (определим по
  `config` / `app/PaymentChannels` перед Phase 4.4).
- **i18n / мультивалюта**: воспроизводим легаси-поведение (translatable +
  MultiCurrency), а не упрощаем.

> Источник истины по каждому пункту — конкретный контроллер легаси; читаем его
> перед реализацией среза.

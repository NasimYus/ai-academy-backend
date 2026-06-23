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
- [ ] **1.5 Роли и гварды доступа** (student/teacher/admin → FastAPI-зависимости; на фронте — route guards)
  - [ ] BE `require_role`  [ ] FE guard-обёртки  [ ] test
- [ ] **1.6 OAuth (Google/Facebook)** — _опционально, можно отложить_
  - [ ] BE socialite-аналог  [ ] FE кнопки входа  [ ] test

---

## Phase 2 — Каталог (public)

- [ ] **2.1 Categories (+ trend categories)**
  - [ ] BE model/migration/endpoints  [ ] FE `entities/category` + фильтр  [ ] test  [ ] admin
- [ ] **2.2 Course detail** (полные метаданные: инструктор, цена, статус, бейджи, что внутри)
  - [ ] BE расширить `Course` + `GET /courses/{slug}`  [ ] FE `pages/course`  [ ] test  [ ] admin
- [ ] **2.3 Search & filters** (категория, цена, уровень, тип)
  - [ ] BE `GET /search` + query-параметры  [ ] FE `widgets/course-filters` + `pages/catalog`  [ ] test
- [ ] **2.4 Featured courses**
  - [ ] BE  [ ] FE блок на главной  [ ] test  [ ] admin
- [ ] **2.5 Instructors / providers + публичный профиль**
  - [ ] BE `instructors/organizations/{id}/profile`  [ ] FE `entities/instructor` + `pages/instructor`  [ ] test
- [ ] **2.6 Reviews & comments (чтение)**
  - [ ] BE list  [ ] FE `entities/review` на странице курса  [ ] test  [ ] admin (модерация)

---

## Phase 3 — Обучение (enrolled, ядро LMS)

- [ ] **3.1 Enrollment + проверка доступа** (покупка/бесплатный → доступ к контенту)
  - [ ] BE `enrollments` + access-зависимость  [ ] FE гейтинг контента  [ ] test
- [ ] **3.2 Chapters + lesson items** (video / text / file / session)
  - [ ] BE модели `Chapter`, `ChapterItem`, `TextLesson`, `File`  [ ] FE `entities/lesson` + `pages/learn`  [ ] test  [ ] admin
- [ ] **3.3 Прогресс обучения** (learning status toggle)
  - [ ] BE  [ ] FE отметки пройдено  [ ] test
- [ ] **3.4 Quizzes: прохождение + результаты**
  - [ ] BE `Quiz`, `Question`, `Result` + start/store-result  [ ] FE `features/take-quiz`  [ ] test  [ ] admin
- [ ] **3.5 Assignments: список/сдача + сообщения**
  - [ ] BE  [ ] FE `features/submit-assignment`  [ ] test  [ ] admin
- [ ] **3.6 Certificates** (achievements, validation, рендер/скачивание)
  - [ ] BE + генерация (PDF)  [ ] FE `pages/certificates`  [ ] test  [ ] admin (шаблоны)
- [ ] **3.7 Personal notes**  — [ ] BE  [ ] FE  [ ] test
- [ ] **3.8 Noticeboards**  — [ ] BE  [ ] FE  [ ] test  [ ] admin
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

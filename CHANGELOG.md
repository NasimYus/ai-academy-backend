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
- ✅ 🧪 **3.9** Forums (Q&A): модели/миграция `CourseForum`/`CourseForumAnswer`; threads (list+counts/create/update/pin) и answers (list/create/update/pin/resolve); access-gate (has_course_access→403), гварды author (update) и course-owner (pin) / owner|author (resolve); `can`-флаги в ответе, агрегаты questions/resolved/open/comments/active_users. NOTE: уведомления отложены

## Phase 4 — Коммерция

- ✅ 🧪 **4.1** Cart: модель/миграция `CartItem` (uniq user+course); `GET /cart` (items + amounts sub_total/total), `POST /cart` (add — гейт already_in_cart/already_purchased/404 на missing|private|inactive), `DELETE /cart/{id}` (owner-scoped). tax/discount/coupon → 4.2/4.3; bundle/product/ticket → store-фаза
- ✅ 🧪 **4.2** Coupons/discounts: модели/миграция `Discount`+`discount_courses/categories/users`; `POST /cart/coupon/validate` (паритет checkValidDiscount + handleDiscountPrice для источников all/course/category; percentage/fixed_amount, max_amount-кап, minimum_order, expired, special_users; reason-коды). NOTE: count/first_purchase (Orders→4.3), groups (Phase 5), bundle/product/meeting — отложены
- ✅ 🧪 **4.3** Checkout + Orders: модели/миграция `Order`/`OrderItem`; `POST /cart/checkout` (pending-заказ из корзины + купон по discount_id + очистка корзины), `GET /panel/orders[/{id}]` (owner-scoped). NOTE: tax/commission=0, per-item скидка пропорционально; оплата→4.4, paid→enrollment→4.5
- ✅ 🧪 **4.4** Payments: модель/миграция `PaymentChannel`; `GET /payments/channels`, `POST /payments/request` (pending→paying + redirect_url), `POST /payments/verify/{gateway}` (paying→paid|fail); сервис абстракции + Sandbox-драйвер. NOTE: реальные шлюзы (креды per-deploy), webhook-подпись — позже; paid→enrollment → 4.5
- ✅ 🧪 **4.4.1** Драйверы шлюзов (паритет легаси `PaymentChannels/`): миграция `b5c6d7e8f9a0` (`credentials` JSONB/`image`/`currencies` на `payment_channels`); пакет `services/payment_channels/` — `PaymentDriver` base (`credential_items`=getCredentialItems, `callback_url`, `payment_request`/`verify`) + `manager.make_channel` (реестр по `class_name`, unknown→Sandbox) + драйверы `Sandbox`/`Zarinpal` (test-mode→локальный callback, live→`require_credentials`); `/payments/channels` отдаёт `credential_items`/`image`/`supported`; `verify/{gateway}` через драйвер. NOTE: 42 реальных драйвера легаси — per-deployment (merchant-креды + внешний HTTP); добавляются классом в реестр
- ✅ 🧪 **4.5** Покупка→enrollment: `payments.complete` на `paid` выдаёт `Enrollment(source=purchase)` на каждый курс заказа (идемпотентно) → доступ через `has_course_access`; `GET /panel/my-courses`. NOTE: charge-account/subscribe/promotion accounting — позже
- ✅ 🧪 **4.6** Purchases: `GET /panel/purchases` (история — оплаченные order-items по курсам: курс/сумма/заказ/дата). Только из paid-заказов

## Phase 5 — Вовлечение

- ✅ 🧪 **5.1** Favorites: модель/миграция `Favorite` (uniq user+course); `GET /favorites`, `POST /favorites/toggle/{course_id}` (favored/unfavored), `DELETE /favorites/{id}` (owner-scoped). NOTE: bundle-избранное — store-фаза
- ✅ 🧪 **5.2** Follow: модель/миграция `Follow` (follower→user, uniq); `POST /users/{id}/follow` {status}, `GET /panel/following`; `followers_count`/`is_following` в публичном профиле (optional-auth)
- ✅ 🧪 **5.3** Notifications: модели/миграция `Notification`+`NotificationStatus`; `GET /notifications?status=all|read|unread` → `{count, notifications}`, `POST /notifications/{id}/seen` (seen/already_seen). Аудитория по `type` (single→user_id, all_users→broadcast не-админам, role-bucket students/instructors/organizations); read-статус per-user. NOTE: `group`/`course_students`/FCM-push отложены (user-groups + firebase)
- ✅ 🧪 **5.4** Support-тикеты: модели/миграция `Support`+`SupportConversation`+`SupportDepartment`; `GET /support` (`{class_support, my_class_support, tickets}`), `/support/{class_support,my_class_support,tickets,departments}`, `GET /support/{id}`, `POST /support` (multipart), `POST /support/{id}/conversations` (multipart, owner→open/teacher→replied), `GET /support/{id}/close`. course_support→course_id, platform_support→department_id; `my_class_support` = тикеты по курсам, где я преподаватель. NOTE: title отдела inline (легаси — translations); supporter/admin-сторона + sendNotification отложены
- ✅ 🧪 **5.5** Blog: модели/миграция `Blog`+`BlogCategory`; общая `comments` расширена `blog_id` (course_id→nullable); `GET /blogs?cat=&limit=&offset=` → `{count, blogs}` (publish), `GET /blogs/categories`, `GET /blogs/{id}` → `{blog}` (комменты-деревом), `POST /blogs/{id}/comments` (коммент/реплай, gate enable_comment); description обрезается до 160. NOTE: title/контент + категории inline (легаси — translations); badges/visit_count/related-posts/rewards/модерация отложены
- ✅ 🧪 **5.6** Newsletter: модель/миграция `Newsletter` (`b9c0d1e2f3a4`, email unique); `POST /newsletter` (optional-auth; дубль email → 422 `already_subscribed`; если авторизован и email == свой → `user.newsletter=true` + link `user_id`). NOTE: NewsletterHistory (рассылка) — admin/Phase 6
- ✅ 🧪 **5.7** Rewards/баллы: модель/миграция `RewardAccounting` (`c0d1e2f3a4b5`, ledger addiction/deduction) + `reward` в enum `enrollment_source`; settings-гейт `rewards_status` (default OFF → no-op как в легаси). `GET /rewards` (гейт→404; points available/total/spent + история + leaderboard + exchangeable), `GET /rewards/reward-courses` (ungated — active+points→brief), `POST /rewards/webinar/{id}/apply` (redeem: no_points/free/already_purchased/no_enough_points→422, иначе `Enrollment(source=reward)` + deduction), `POST /rewards/exchange` (гейт→403; deduction, кредит кошелька → NOTE). Отложено: earning-правила (`Reward`-таблица, авто-начисление по событиям) и wallet/Accounting — гейт-заглушки/Phase 6

## Phase 6 — Инструктор

- ✅ 🧪 **6.1** Course CRUD (инструктор): `POST /panel/webinar` (create, паритет `storeAll`: required type/title/thumbnail/image_cover/description/category_id; status `pending` если `rules` принят и не `draft`, иначе `is_draft`; slug автоген уникальный; webinar→`start_date` обязателен), `GET /panel/classes` (свои курсы), `GET /panel/webinar/{id}/edit`, `PUT /panel/webinar/{id}`, `DELETE /panel/webinar/{id}`; гейт `require_level("teacher")` (teacher|organization → иначе 403) + ownership (creator|teacher → 404 чужие). Отложено: tags/filters/partner-instructors (отдельные подсистемы), org→teacher_id назначение
- ✅ 🧪 **6.2** Quizzes CRUD (инструктор): `POST /panel/quizzes` (создание shell: title/course_id/chapter_id?/pass_mark/attempt?/time?/active→status/certificate; chapter сбрасывается если не на курсе), `PUT /panel/quizzes/{id}`, `DELETE /panel/quizzes/{id}` (creator-scoped), `GET /panel/quizzes/list` (дашборд: свои квизы + попытки + stats count/passed/waiting/success_rate/avg_grade); `require_level("teacher")` + ownership курса. NOTE: на update добавлен ownership-гейт (легаси `Quiz::find` без проверки = IDOR); questions CRUD — web-panel, вне API
- ✅ 🧪 **6.3** Assignment grading (инструктор): `GET /panel/assignments` (дашборд: свои задания + histories + counts pending/passed/failed), `GET /panel/assignments/{id}/submissions` (треды работ студентов с сообщениями), `POST /panel/assignments/histories/{id}/rate` ({grade} → passed/not_passed по pass_grade, creator-scoped); `require_level("teacher")`. NOTE: фича-гейт `webinar_assignment_status` не навешан (студ-флоу ungated); reward PASS_ASSIGNMENT отложен (earning-правила, 5.7)
- ✅ 🧪 **6.4** Instructor comments: `GET /panel/comments` (комменты на курсах инструктора, деревом с ответами), `POST /panel/comments/{id}/reply` ({reply}, scoped к своим курсам); `require_level("teacher")`. NOTE: `viewed_at` не трекаем; reply-scope сужен (легаси ownership закомментирован)
- ✅ 🧪 **6.5** Bundles (инструктор): модели/миграция `Bundle`+`BundleWebinar` (`d1e2f3a4b5c6`); `GET /panel/bundles` (свои наборы + bundles_count/hours; sales=0 — bundle-покупок нет), `DELETE /panel/bundles/{id}` (owner-scoped); `require_level("teacher")`. NOTE: store/update/show в легаси пустые; title inline (translations)
- ✅ 🧪 **6.6** Store/products (каталог): модели/миграция `Product`/`ProductCategory` (`a4b5c6d7e8f9`, type virtual/physical; title/description inline); публично `GET /products` (active+ordering, фильтр `?category_id`), `GET /products/{id}` (404 неактивные), `GET /product_categories` (top+subs); инструктор `GET /panel/store/products` (свои, `require_level("teacher")`). NOTE: покупка (ProductOrder/cart-product), отзывы/комменты/спецификации/галерея, product CRUD (web-panel) — отложены
- ✅ 🧪 **6.7** Statistics (инструктор): `GET /panel/webinar/{id}/statistic` (owned-курс агрегаты — students/sales_count/sales_amount(paid order_items)/rate/reviews/comments/chapters(active)/sessions/files/text_lessons/quizzes(active)/assignments(active)/forums); `require_level("teacher")` + ownership (404 чужие). Сервис `statistics.build_course_statistics`. NOTE: forums_students/quizzes_avg_grade/students_roles из легаси опущены; 6.6 store/products — отдельная подсистема, отложена

## Phase 7 — Live & advanced

- ✅ 🧪 **7.1** Meetings/консультации: модели/миграция `Meeting`/`MeetingTime`/`ReserveMeeting` (`e2f3a4b5c6d7`); инструктор `GET/PUT /panel/meeting` (цена/disabled) + `POST/DELETE /panel/meeting/times` (слоты); публично `GET /users/{id}/meeting`; юзер `POST /meetings/reserve`, `GET /panel/meetings` (`{reservations,requests}`), `GET /panel/meetings/{id}`, `POST /panel/meetings/{id}/finish`. NOTE: paid-checkout (sale_id) + Agora live-link гейтнуты (free path); `details.user`=создатель встречи (легаси-квирк)
- ✅ 🧪 **7.2** Subscriptions: модели/миграция `Subscribe`/`UserSubscribe`/`SubscribeUse` (`f3a4b5c6d7e8`); `GET /subscribe` (optional-auth — планы + активная подписка `{used/remaining/days_left}` + `day_of_use`), `POST /subscribe/{id}/activate` (free-план → `UserSubscribe`; платный → 422 not_free), `POST /subscribe/apply` ({course_id}: not_subscribable/no_active_subscribe/free/already_purchased→422, иначе `SubscribeUse`+`Enrollment(source=subscribe)`). Активность = в окне `days` и `used<usable_count`. NOTE: paid-checkout (webPay) и registration-packages (teacher) — отложены
- ✅ 🧪 **7.3** Bundle purchase: публично `GET /bundles` (active), `GET /bundles/{id}` (+ courses), `GET /bundles/{id}/webinars`; покупка `POST /bundles/{id}/free` (price>0→422 not_free, иначе `Enrollment(source=bundle)` на все курсы; повтор→422 already_purchased) и `POST /bundles/{id}/buyWithPoint` (no_points/no_enough_points→422, иначе enroll all + reward deduction). NOTE: paid-bundle через cart/checkout — отложено (как course paid)

## Сквозные задачи (foundation)

- ✅ **F.1** Файловое хранилище (локальный диск, `/media`; S3 — позже)
- ✅ 🧪 **F.2** Фоновые задачи: `tasks.enqueue` (бэкенды `inline`/`asyncio`); email теперь через очередь. NOTE: durable arq/Celery+Redis — за тем же интерфейсом, per-deploy
- ✅ 🧪 **F.3** Email-отправка: сервис `email` (бэкенды `console`/`smtp` через aiosmtplib, in-memory outbox для тестов); шлёт код верификации, ссылку сброса пароля, чек об оплате. SMS — заглушка (нет провайдера); очередь — F.2
- ✅ 🧪 **F.4** i18n контента: `category_translations`/`course_translations`+миграция; `Locale`-зависимость (`?locale=`/Accept-Language), `i18n.localize` (fallback locale→default→база); применено к категориям и курсам (list/detail). NOTE: прочие translatable — инкрементально тем же паттерном
- ✅ 🧪 **F.5** Мультивалюта: `currencies`+миграция; `GET /currencies`, `CurrencyCtx` (`?currency=`, fallback default), сервис convert/format (exchange_rate, sign/position/decimals); цены курса конвертируются + `currency` в ответе. NOTE: суммы корзины/заказов — в базовой валюте

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

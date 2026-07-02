from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Academy API"
    environment: str = "development"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://aiacademy:aiacademy@localhost:5432/aiacademy"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # --- registration (legacy "general settings" parity) ---
    # Which identifier registration uses: "email" or "mobile".
    register_method: str = "email"
    # When true, accounts are active immediately and codes are not required.
    disable_registration_verification_process: bool = False
    # Default value of the per-user `affiliate` flag at registration (Phase 5).
    users_affiliate_status: bool = False
    # When true, submitted course reviews are published immediately (else pending
    # until an admin approves) — legacy general option `direct_publication_of_reviews`.
    direct_publication_of_reviews: bool = False

    # --- login (legacy security settings parity) ---
    login_device_limit: bool = False
    number_of_allowed_devices: int = 1

    # --- rewards / points (Phase 5.7, legacy getRewardsSettings) ---
    # Master gate: when false the rewards subsystem is a no-op (legacy clean DB).
    rewards_status: bool = False
    rewards_exchangeable: bool = False
    rewards_exchangeable_unit: int = 1  # points per 1 wallet unit (avoid div-by-zero)

    # --- file storage (F.1) ---
    media_root: str = "media"
    media_url: str = "/media"

    # --- i18n content (F.4) ---
    default_locale: str = "en"

    # --- multi-currency (F.5) ---
    # Currency that stored prices are denominated in (exchange_rate base).
    default_currency: str = "USD"

    # --- background tasks (F.2) ---
    # "inline" runs work synchronously (dev/tests); "asyncio" fire-and-forgets it.
    task_backend: str = "inline"

    # --- email (F.3) ---
    # "console" records to an in-memory outbox (dev/tests); "smtp" sends via SMTP.
    email_backend: str = "console"
    mail_from: str = "no-reply@aiacademy.tj"
    mail_from_name: str = "AI Academy"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    # Public base URL for links embedded in emails (reset, receipts).
    frontend_url: str = "http://localhost:3000"

    # Comma-separated in env; use `cors_origins` (the parsed list) in code.
    cors_origins_raw: str = "http://localhost:3000,http://localhost:5173"
    # Regex for local dev origins (any localhost/127.0.0.1 port). Prod domains
    # go in `cors_origins_raw`. Matches http(s)://localhost|127.0.0.1[:port].
    cors_origin_regex: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

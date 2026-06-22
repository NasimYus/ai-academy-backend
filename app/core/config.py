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

    # --- login (legacy security settings parity) ---
    login_device_limit: bool = False
    number_of_allowed_devices: int = 1

    # Comma-separated in env; use `cors_origins` (the parsed list) in code.
    cors_origins_raw: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

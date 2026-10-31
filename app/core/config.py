from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_SECRET = "dev-only-change-me-6f4b1c0e8a2d4f7b9c3e5a1d"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Brightloop Subscription Management"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = True

    secret_key: str = DEFAULT_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    database_url: str = "sqlite:///./brightloop.db"

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    frontend_url: str = "http://localhost:5173"
    frontend_build_dir: str = "frontend/build"
    serve_frontend: bool = True
    password_reset_expire_minutes: int = 30

    seed_demo_data: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow `CORS_ORIGINS=a,b` in .env as well as a JSON list."""
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _require_production_secret(self) -> "Settings":
        if self.is_production and (
            self.secret_key == DEFAULT_SECRET or len(self.secret_key) < 32
        ):
            raise ValueError(
                "SECRET_KEY must be a random value of at least 32 characters in production"
            )
        return self

    @model_validator(mode="after")
    def _use_writable_sqlite_on_vercel(self) -> "Settings":
        """Keep SQLite usable on Vercel's read-only, per-instance filesystem.

        Vercel only allows writes under /tmp, and that storage is not shared
        between function instances. Point DATABASE_URL at Postgres for durable
        data; this fallback keeps preview deployments working with an ephemeral
        database that is rebuilt on each cold start.
        """
        if (
            os.getenv("VERCEL")
            and os.name == "posix"
            and self.is_sqlite
            and ":memory:" not in self.database_url
        ):
            filename = self.database_url.rsplit("/", 1)[-1] or "brightloop.db"
            self.database_url = f"sqlite:////tmp/{filename}"
        return self

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def frontend_build_path(self) -> Path:
        path = Path(self.frontend_build_dir)
        return path if path.is_absolute() else BASE_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AMS_", env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore"
    )

    env: str = "development"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://ams:ams@localhost:5432/ams"
    secret_key: SecretStr = SecretStr("development-only-change-me-and-rotate-this-key")
    cookie_samesite: str = "lax"
    access_token_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:3000"]
    storage_backend: str = "local"
    storage_path: Path = Path("uploads")
    s3_bucket: str | None = None
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: SecretStr | None = None
    max_document_bytes: int = 10 * 1024 * 1024
    vision_minimum_confidence: float = 0.45
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str = "noreply@ams.local"
    frontend_base_url: str = "http://localhost:3000"
    twilio_account_sid: str | None = None
    twilio_auth_token: SecretStr | None = None
    twilio_from_number: str | None = None

    @field_validator("access_token_minutes")
    @classmethod
    def positive_token_lifetime(cls, value: int) -> int:
        if value < 1:
            raise ValueError("access_token_minutes must be positive")
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def add_psycopg_driver(cls, value: str) -> str:
        # Render Postgres supplies postgresql://; this project uses psycopg 3.
        if isinstance(value, str) and value.startswith(("postgres://", "postgresql://")):
            return value.replace("postgres://", "postgresql+psycopg://", 1).replace(
                "postgresql://", "postgresql+psycopg://", 1
            )
        return value

    @field_validator("cookie_samesite")
    @classmethod
    def valid_cookie_samesite(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("AMS_COOKIE_SAMESITE must be lax, strict, or none")
        return normalized

    @model_validator(mode="after")
    def require_deployment_secret(self) -> "Settings":
        secret = self.secret_key.get_secret_value()
        if self.env != "development" and (
            len(secret) < 32 or secret == "replace-this-with-a-long-random-secret"
        ):
            raise ValueError(
                "AMS_SECRET_KEY must contain at least 32 characters outside development"
            )
        if self.storage_backend not in {"local", "s3"}:
            raise ValueError("AMS_STORAGE_BACKEND must be either local or s3")
        if self.storage_backend == "s3" and not (
            self.s3_bucket and self.s3_access_key_id and self.s3_secret_access_key
        ):
            raise ValueError("S3 storage requires bucket and access credentials")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

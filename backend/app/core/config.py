from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEVELOPMENT_SECRET = "development-only-change-me-and-rotate-this-key"


def validate_deployment_secret(env: str, secret: str) -> None:
    if env != "development" and (
        len(secret) < 32
        or secret in {_DEVELOPMENT_SECRET, "replace-this-with-a-long-random-secret"}
    ):
        raise ValueError("AMS_SECRET_KEY must contain at least 32 characters outside development")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AMS_", env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore"
    )

    env: str = "development"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://ams:ams@localhost:5432/ams"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    http_request_concurrency: int = 15
    secret_key: SecretStr = SecretStr(_DEVELOPMENT_SECRET)
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
        if self.env not in {"development", "production"}:
            raise ValueError("AMS_ENV must be development or production")
        secret = self.secret_key.get_secret_value()
        validate_deployment_secret(self.env, secret)
        if self.storage_backend not in {"local", "s3"}:
            raise ValueError("AMS_STORAGE_BACKEND must be either local or s3")
        if self.storage_backend == "s3" and not (
            self.s3_bucket and self.s3_access_key_id and self.s3_secret_access_key
        ):
            raise ValueError("S3 storage requires bucket and access credentials")
        if self.database_pool_size < 1 or self.database_max_overflow < 0:
            raise ValueError("Database pool size must be positive and overflow cannot be negative")
        if (
            not 1
            <= self.http_request_concurrency
            <= (self.database_pool_size + self.database_max_overflow)
        ):
            raise ValueError("HTTP request concurrency cannot exceed the database pool capacity")
        if self.env == "production":
            if self.cookie_samesite != "none":
                raise ValueError(
                    "Production cross-origin sessions require AMS_COOKIE_SAMESITE=none"
                )
            if self.storage_backend != "s3":
                raise ValueError("Production requires private S3-compatible document storage")
            if not self.cors_origins:
                raise ValueError("Production requires an exact HTTPS AMS_CORS_ORIGINS allowlist")
            for origin in self.cors_origins:
                parsed_origin = urlsplit(origin)
                if (
                    "*" in origin
                    or origin != origin.strip()
                    or parsed_origin.scheme != "https"
                    or not parsed_origin.netloc
                    or parsed_origin.hostname is None
                    or parsed_origin.username is not None
                    or parsed_origin.password is not None
                    or parsed_origin.path
                    or parsed_origin.query
                    or parsed_origin.fragment
                ):
                    raise ValueError("Production CORS origins must be exact HTTPS origins")
            parsed_frontend = urlsplit(self.frontend_base_url)
            if (
                parsed_frontend.scheme != "https"
                or not parsed_frontend.netloc
                or parsed_frontend.path
                or parsed_frontend.query
                or parsed_frontend.fragment
                or self.frontend_base_url not in self.cors_origins
            ):
                raise ValueError(
                    "Production AMS_FRONTEND_BASE_URL must be an exact origin in AMS_CORS_ORIGINS"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

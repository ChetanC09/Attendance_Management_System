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
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str = "noreply@ams.local"
    frontend_base_url: str = "http://localhost:3000"
    twilio_account_sid: str | None = None
    twilio_auth_token: SecretStr | None = None
    twilio_from_number: str | None = None
    # CIDR subnets allowed for student face self-checkin (college network)
    allowed_checkin_subnets: list[str] = ["192.168.1.0/24", "127.0.0.1/32", "::1/128"]

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

    @field_validator("cors_origins", mode="before")
    @classmethod
    def normalize_cors_origins(cls, value: object) -> list[str]:
        """Strip paths/query/fragments from each CORS origin so that values like
        'https://app.vercel.app/auth/login' are silently corrected to
        'https://app.vercel.app' instead of crashing at startup."""
        if isinstance(value, str):
            import json
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                value = [value]
        if not isinstance(value, list):
            value = [value]
        normalized: list[str] = []
        for origin in value:
            origin = str(origin).strip()
            parsed = urlsplit(origin)
            if parsed.scheme and parsed.netloc:
                # Rebuild as bare origin — drop path, query, fragment
                normalized.append(f"{parsed.scheme}://{parsed.netloc}")
            else:
                normalized.append(origin)
        return normalized

    @field_validator("frontend_base_url", mode="before")
    @classmethod
    def normalize_frontend_base_url(cls, value: object) -> str:
        """Strip any path from AMS_FRONTEND_BASE_URL so 'https://app.vercel.app/auth/login'
        becomes 'https://app.vercel.app'."""
        if not isinstance(value, str):
            return str(value)
        parsed = urlsplit(value.strip())
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return value

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
                    "Production cross-origin sessions require AMS_COOKIE_SAMESITE=none "
                    "(set this env var to 'none' in your Render dashboard)"
                )
            # S3 is strongly recommended for production document storage, but local
            # storage is permitted so the service can start without object-storage
            # credentials (e.g. for demo / academic deployments).
            if not self.cors_origins:
                raise ValueError("Production requires AMS_CORS_ORIGINS (your Vercel URL)")
            for origin in self.cors_origins:
                parsed_origin = urlsplit(origin)
                if (
                    "*" in origin
                    or parsed_origin.scheme != "https"
                    or not parsed_origin.netloc
                ):
                    raise ValueError(
                        f"Production CORS origin must be an https:// URL, got: {origin!r}"
                    )
            # Ensure frontend_base_url is within the allowed CORS list
            if self.frontend_base_url not in self.cors_origins:
                raise ValueError(
                    "Production AMS_FRONTEND_BASE_URL must be in AMS_CORS_ORIGINS. "
                    f"Got frontend={self.frontend_base_url!r}, cors={self.cors_origins!r}"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

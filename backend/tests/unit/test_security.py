import pytest

from app.core.config import Settings, validate_deployment_secret
from app.core.security import hash_password, verify_password


def test_password_hash_uses_argon2_and_verifies_only_matching_password() -> None:
    encoded = hash_password("Correct horse battery staple 42!")
    assert encoded.startswith("$argon2id$")
    assert verify_password("Correct horse battery staple 42!", encoded)
    assert not verify_password("not the password", encoded)


def test_production_settings_reject_the_known_development_signing_key() -> None:
    with pytest.raises(ValueError, match="AMS_SECRET_KEY"):
        validate_deployment_secret("production", "development-only-change-me-and-rotate-this-key")

    validate_deployment_secret("production", "a" * 48)


def test_request_concurrency_cannot_exceed_configured_pool_capacity() -> None:
    with pytest.raises(ValueError, match="cannot exceed the database pool capacity"):
        Settings(
            _env_file=None,
            database_pool_size=5,
            database_max_overflow=10,
            http_request_concurrency=16,
        )


def production_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "env": "production",
        "secret_key": "a" * 48,
        "cookie_samesite": "none",
        "storage_backend": "s3",
        "s3_bucket": "private-ams-documents",
        "s3_access_key_id": "test-access-key",
        "s3_secret_access_key": "test-secret-key",
        "cors_origins": ["https://ams.example"],
        "frontend_base_url": "https://ams.example",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_settings_require_https_exact_origins_and_cookie_storage_defaults() -> None:
    production_settings()

    with pytest.raises(ValueError, match="exact HTTPS origins"):
        production_settings(cors_origins=["*"])

    with pytest.raises(ValueError, match="exact HTTPS origins"):
        production_settings(cors_origins=["https://*.ams.example"])

    with pytest.raises(ValueError, match="exact HTTPS origins"):
        production_settings(cors_origins=["http://ams.example"])

    with pytest.raises(ValueError, match="AMS_COOKIE_SAMESITE=none"):
        production_settings(cookie_samesite="lax")

    with pytest.raises(ValueError, match="private S3-compatible"):
        production_settings(storage_backend="local")

    with pytest.raises(ValueError, match="must be an exact origin"):
        production_settings(frontend_base_url="https://other.example")


def test_production_settings_do_not_fall_back_to_localhost_or_local_storage() -> None:
    with pytest.raises(ValueError, match="exact HTTPS origins"):
        Settings(
            _env_file=None,
            env="production",
            secret_key="a" * 48,
            cookie_samesite="none",
            storage_backend="s3",
            s3_bucket="private-ams-documents",
            s3_access_key_id="test-access-key",
            s3_secret_access_key="test-secret-key",
        )


def test_settings_reject_unknown_deployment_environment() -> None:
    with pytest.raises(ValueError, match="AMS_ENV must be development or production"):
        Settings(_env_file=None, env="stage")

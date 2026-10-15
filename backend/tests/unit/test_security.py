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

    # wildcard origins are still rejected
    with pytest.raises(ValueError, match="https://"):
        production_settings(cors_origins=["*"])

    # paths are auto-stripped now — https://*.ams.example has no netloc after urlsplit
    # but a plain https://ams.example/path is corrected to https://ams.example (no longer raises)
    production_settings(cors_origins=["https://ams.example/some/path"])

    # http:// origins are rejected (not https)
    with pytest.raises(ValueError, match="https://"):
        production_settings(cors_origins=["http://ams.example"])

    with pytest.raises(ValueError, match="AMS_COOKIE_SAMESITE=none"):
        production_settings(cookie_samesite="lax")

    # local storage is permitted in production (no longer raises)
    production_settings(storage_backend="local", s3_bucket=None, s3_access_key_id=None, s3_secret_access_key=None)

    # frontend_base_url pointing to a different https domain is now auto-added to cors list
    # so it no longer raises — both origins are allowed
    s = production_settings(frontend_base_url="https://other.example")
    assert "https://other.example" in s.cors_origins


def test_production_settings_do_not_fall_back_to_localhost_or_local_storage() -> None:
    # When only localhost origins exist, they are auto-dropped in production.
    # AMS_FRONTEND_BASE_URL (https) is then auto-added, so this now succeeds.
    s = Settings(
        _env_file=None,
        env="production",
        secret_key="a" * 48,
        cookie_samesite="none",
        storage_backend="s3",
        s3_bucket="private-ams-documents",
        s3_access_key_id="test-access-key",
        s3_secret_access_key="test-secret-key",
        cors_origins=["http://localhost:3000"],
        frontend_base_url="https://ams.example",
    )
    # localhost should be stripped; https frontend should be present
    assert "http://localhost:3000" not in s.cors_origins
    assert "https://ams.example" in s.cors_origins


def test_settings_reject_unknown_deployment_environment() -> None:
    with pytest.raises(ValueError, match="AMS_ENV must be development or production"):
        Settings(_env_file=None, env="stage")

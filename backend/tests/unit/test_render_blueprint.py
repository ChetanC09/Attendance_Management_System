from pathlib import Path

import pytest
import yaml


def test_notification_worker_reuses_api_production_configuration() -> None:
    repo_root = next(
        (
            parent
            for parent in Path(__file__).resolve().parents
            if (parent / "render.yaml").is_file()
        ),
        None,
    )
    if repo_root is None:
        pytest.skip("Render Blueprint is not included in the backend-only test bundle")
    blueprint_path = repo_root / "render.yaml"
    blueprint = yaml.safe_load(blueprint_path.read_text(encoding="utf-8"))
    services = {service["name"]: service for service in blueprint["services"]}
    api_env = {item["key"]: item for item in services["ams-api"]["envVars"]}
    worker_env = {item["key"]: item for item in services["ams-notifications"]["envVars"]}

    shared_production_settings = (
        "AMS_SECRET_KEY",
        "AMS_COOKIE_SAMESITE",
        "AMS_CORS_ORIGINS",
        "AMS_FRONTEND_BASE_URL",
        "AMS_STORAGE_BACKEND",
        "AMS_S3_BUCKET",
        "AMS_S3_REGION",
        "AMS_S3_ENDPOINT_URL",
        "AMS_S3_ACCESS_KEY_ID",
        "AMS_S3_SECRET_ACCESS_KEY",
        "AMS_SMTP_HOST",
        "AMS_SMTP_PORT",
        "AMS_SMTP_USERNAME",
        "AMS_SMTP_PASSWORD",
        "AMS_SMTP_FROM_EMAIL",
        "AMS_TWILIO_ACCOUNT_SID",
        "AMS_TWILIO_AUTH_TOKEN",
        "AMS_TWILIO_FROM_NUMBER",
    )

    for key in shared_production_settings:
        assert key in api_env
        assert worker_env[key]["fromService"] == {
            "type": "web",
            "name": "ams-api",
            "envVarKey": key,
        }

    assert api_env["AMS_CORS_ORIGINS"]["sync"] is False
    assert api_env["AMS_FRONTEND_BASE_URL"]["sync"] is False
    assert api_env["AMS_COOKIE_SAMESITE"]["value"] == "none"
    assert api_env["AMS_STORAGE_BACKEND"]["value"] == "s3"
    assert api_env["AMS_S3_ACCESS_KEY_ID"]["sync"] is False
    assert api_env["AMS_S3_SECRET_ACCESS_KEY"]["sync"] is False

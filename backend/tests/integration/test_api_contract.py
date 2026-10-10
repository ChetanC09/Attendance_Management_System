from fastapi.testclient import TestClient
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from app.main import app


def test_health_and_openapi_cookie_contract() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/api/health").json() == {"status": "ok"}
        schema = client.get("/openapi.json").json()

    assert "/api/auth/login" in schema["paths"]
    assert "/api/faculty/attendance/session" in schema["paths"]
    assert schema["paths"]["/api/auth/me"]["get"]["security"] == [{"AMSSessionCookie": []}]


def test_cross_origin_write_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post("/api/auth/logout", headers={"Origin": "https://attacker.invalid"})

    assert response.status_code == 403


def test_logout_returns_no_content_status() -> None:
    with TestClient(app) as client:
        response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert response.content == b""


def test_database_pool_timeout_returns_retryable_service_unavailable(monkeypatch) -> None:
    class TimedOutSessionContext:
        def __enter__(self):
            raise SQLAlchemyTimeoutError("private pool diagnostic")

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr("app.core.database.SessionLocal", lambda: TimedOutSessionContext())
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.headers["retry-after"] == "1"
    assert response.json() == {"detail": "Database capacity is temporarily unavailable"}
    assert "private pool diagnostic" not in response.text


def test_api_responses_include_security_headers() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(self), microphone=(), geolocation=()"

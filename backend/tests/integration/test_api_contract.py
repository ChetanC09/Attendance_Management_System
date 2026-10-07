from fastapi.testclient import TestClient

from app.main import app


def test_health_and_openapi_cookie_contract() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/api/health").json() == {"status": "ok"}
        schema = client.get("/openapi.json").json()

    assert "/api/auth/login" in schema["paths"]
    assert "/api/faculty/attendance/session" in schema["paths"]
    assert schema["paths"]["/api/auth/me"]["get"]["security"] == [{"AMSSessionCookie": []}]

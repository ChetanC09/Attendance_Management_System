"""Read-only role and API integration smoke checks for a seeded development stack."""

import os
import sys

import httpx

BASE_URL = os.getenv("AMS_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
PASSWORD = os.getenv("AMS_DEMO_PASSWORD", "SolarisDemo2026!")


def require(client: httpx.Client, path: str, expected: int = 200) -> httpx.Response:
    response = client.get(path)
    if response.status_code != expected:
        raise AssertionError(f"GET {path}: expected {expected}, got {response.status_code}: {response.text[:300]}")
    return response


def login(email: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE_URL, follow_redirects=True)
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    if response.status_code != 200:
        raise AssertionError(f"Login for {email} failed: {response.status_code} {response.text[:300]}")
    client.get("/api/auth/me").raise_for_status()
    return client


def main() -> int:
    checks = {
        "admin": [
            "/api/admin/overview",
            "/api/admin/users?limit=500",
            "/api/admin/departments",
            "/api/admin/courses",
            "/api/admin/allocations",
            "/api/admin/timetable",
            "/api/admin/audit-logs?limit=20",
        ],
        "faculty": [
            "/api/faculty/lectures/today",
            "/api/faculty/timetable/overview",
            "/api/faculty/analytics/allocations",
            "/api/faculty/analytics/defaulters",
            "/api/faculty/analytics/trend",
            "/api/faculty/requests",
            "/api/faculty/announcements",
        ],
        "student1": [
            "/api/student/attendance",
            "/api/student/attendance/threshold",
            "/api/student/analytics/overall",
            "/api/student/timetable",
            "/api/student/requests",
            "/api/student/announcements",
            "/api/notifications",
        ],
    }
    emails = {"admin": "admin@ams.dev", "faculty": "faculty@ams.dev", "student1": "student1@ams.dev"}
    clients = {role: login(emails[role]) for role in checks}
    total = 0
    try:
        for role, paths in checks.items():
            if role == "faculty":
                allocation_rows = require(clients[role], "/api/faculty/analytics/allocations").json()
                if not allocation_rows:
                    raise AssertionError("Seeded faculty has no course allocations")
                paths = [
                    path
                    if path not in {"/api/faculty/analytics/defaulters", "/api/faculty/analytics/trend"}
                    else f"{path}?allocation_id={allocation_rows[0]['allocation_id']}"
                    for path in paths
                ]
            for path in paths:
                require(clients[role], path)
                total += 1
            print(f"PASS {role}: {len(paths)} authenticated API routes")

        student_denial = clients["student1"].get("/api/admin/overview")
        if student_denial.status_code != 403:
            raise AssertionError(f"Student admin access should be 403, got {student_denial.status_code}")
        total += 1
        faculty_denial = clients["faculty"].get("/api/admin/overview")
        if faculty_denial.status_code != 403:
            raise AssertionError(f"Faculty admin access should be 403, got {faculty_denial.status_code}")
        total += 1
        print("PASS role isolation: student and faculty denied admin overview")

        invalid_origin = clients["student1"].post(
            "/api/notifications/preferences/EMAIL?enabled=false",
            headers={"Origin": "https://untrusted.invalid"},
        )
        if invalid_origin.status_code != 403:
            raise AssertionError(f"Untrusted browser origin should be 403, got {invalid_origin.status_code}")
        total += 1
        print("PASS CSRF origin guard")
    finally:
        for client in clients.values():
            client.close()
    print(f"PASS {total} smoke checks against {BASE_URL}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1) from error

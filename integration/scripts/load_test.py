"""Measure authenticated AMS read bursts against a seeded development stack.

Each simulated user gets a separate cookie jar. Seeded identities are reused, so
the runner measures concurrent sessions rather than unique institutional users.
It does not write attendance, call external providers, or invoke real vision.
"""

import argparse
import asyncio
import math
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

source_roots = [Path("/srv/ams")]
if len(Path(__file__).resolve().parents) > 2:
    source_roots.append(Path(__file__).resolve().parents[2] / "backend")
# Prefer the current repository source over any installed backend wheel.
for source_root in source_roots:
    if (source_root / "app").is_dir():
        sys.path.insert(0, str(source_root))
        break

from app.core.config import settings  # noqa: E402
from app.core.database import engine as application_engine  # noqa: E402

BASE_URL = os.getenv("AMS_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
PASSWORD = os.getenv("AMS_DEMO_PASSWORD", "")
STUDENTS = [f"student{index}@ams.dev" for index in range(1, 7)]
REQUEST_TIMEOUT_SECONDS = 45


def make_database_monitor():
    return create_engine(
        settings.database_url,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def read_database_metrics(monitor) -> dict[str, int]:
    statement = text(
        """
        SELECT current_setting('max_connections')::int AS max_connections,
               (SELECT count(*) FROM pg_stat_activity
                WHERE datname = current_database())::int AS connections,
               (SELECT count(*) FROM pg_stat_activity
                WHERE datname = current_database() AND state = 'active')::int AS active_connections,
               pg_database_size(current_database())::bigint AS database_bytes,
               (SELECT count(*) FROM users)::int AS users,
               (SELECT count(*) FROM attendance)::int AS attendance_rows
        """
    )
    with monitor.connect() as connection:
        row = connection.execute(statement).mappings().one()
    return dict(row)


async def fetch_json(client: httpx.AsyncClient, path: str) -> object:
    response = await client.get(path)
    response.raise_for_status()
    return response.json()


async def bootstrap_ids() -> tuple[str, str]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS) as client:
        login = await client.post(
            "/api/auth/login", json={"email": STUDENTS[0], "password": PASSWORD}
        )
        login.raise_for_status()
        courses = await fetch_json(client, "/api/student/attendance")
        logout = await client.post("/api/auth/logout")
        logout.raise_for_status()
        if not courses:
            raise RuntimeError("Seeded student has no courses to measure")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS) as client:
        login = await client.post(
            "/api/auth/login", json={"email": "faculty@ams.dev", "password": PASSWORD}
        )
        login.raise_for_status()
        allocations = await fetch_json(client, "/api/faculty/analytics/allocations")
        logout = await client.post("/api/auth/logout")
        logout.raise_for_status()
        if not allocations:
            raise RuntimeError("Seeded faculty has no allocations to measure")
        return courses[0]["course_id"], allocations[0]["allocation_id"]


def session_role(index: int) -> tuple[str, str]:
    role_slot = index % 10
    if role_slot < 7:
        return "student", STUDENTS[index % len(STUDENTS)]
    if role_slot < 9:
        return "faculty", "faculty@ams.dev"
    return "admin", "admin@ams.dev"


def request_for(role: str, index: int, course_id: str, allocation_id: str) -> tuple[str, str]:
    routes = {
        "student": [
            ("dashboard", "/api/student/attendance"),
            ("history", "/api/student/attendance/history?limit=20&offset=0"),
            ("recovery", f"/api/student/analytics/recovery?course_id={course_id}"),
        ],
        "faculty": [
            ("defaulters", f"/api/faculty/analytics/defaulters?allocation_id={allocation_id}"),
            ("analytics", f"/api/faculty/analytics/trend?allocation_id={allocation_id}"),
        ],
        "admin": [("admin_dashboard", "/api/admin/overview")],
    }
    choices = routes[role]
    return choices[index % len(choices)]


def error_label(error: Exception) -> str:
    if isinstance(error, httpx.TimeoutException):
        return "timeout"
    if isinstance(error, httpx.HTTPStatusError):
        response = error.response
        content = response.text.lower()
        if (
            "queuepool" in content
            or "connection pool" in content
            or "database capacity is temporarily unavailable" in content
        ):
            return "database_pool_error"
        if response.status_code >= 500:
            return f"http_{response.status_code}"
        return f"http_{response.status_code}"
    if isinstance(error, httpx.RequestError):
        return f"request_{type(error).__name__}"
    if isinstance(error, (ValueError, KeyError, TypeError)):
        return "invalid_payload"
    return type(error).__name__


def validate_payload(name: str, payload: object) -> None:
    """Check each successful read returned JSON in the route's expected shape."""
    schemas = {
        "dashboard": (
            list,
            {"course_id", "course_code", "conducted_lectures", "attendance_percentage"},
        ),
        "history": (list, {"lecture_id", "course_code", "starts_at", "status"}),
        "recovery": (
            dict,
            {
                "attended_lectures",
                "conducted_lectures",
                "current_percentage",
                "required_lectures",
                "achievable",
            },
        ),
        "defaulters": (
            list,
            {"student_id", "institutional_id", "attended_lectures", "attendance_percentage"},
        ),
        "analytics": (list, {"lecture_id", "recorded", "attended", "attendance_percentage"}),
        "admin_dashboard": (
            dict,
            {"departments", "courses", "lectures", "attendance_records", "active_users"},
        ),
    }
    expected_type, required_keys = schemas[name]
    if not isinstance(payload, expected_type):
        raise ValueError(f"{name} response must be {expected_type.__name__}")
    rows = payload if isinstance(payload, list) else [payload]
    for row in rows:
        if not isinstance(row, dict) or not required_keys.issubset(row):
            raise ValueError(f"{name} response is missing required fields")


async def create_session(
    index: int,
    gate: asyncio.Semaphore,
    measurements: dict[str, list[float]],
    errors: Counter,
) -> tuple[str, httpx.AsyncClient, float, list[str]] | None:
    role, email = session_role(index)
    trace_events: list[str] = []

    async def trace_httpcore(event_name: str, _info: dict) -> None:
        trace_events.append(event_name)

    async def attach_trace(request: httpx.Request) -> None:
        request.extensions["trace"] = trace_httpcore

    client = httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=REQUEST_TIMEOUT_SECONDS,
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
        event_hooks={"request": [attach_trace]},
    )
    try:
        async with gate:
            started = time.perf_counter()
            response = await client.post(
                "/api/auth/login", json={"email": email, "password": PASSWORD}
            )
            response.raise_for_status()
            body = response.json()
            if (
                not isinstance(body, dict)
                or not isinstance(body.get("user"), dict)
                or body["user"].get("role") != role.upper()
                or not client.cookies.get("ams_session")
            ):
                raise ValueError("Login did not establish the expected authenticated session")
            measurements["login"].append(time.perf_counter() - started)
        return role, client, time.perf_counter(), trace_events
    except Exception as error:
        errors[f"login_{error_label(error)}"] += 1
        await client.aclose()
        return None


async def measured_request(
    role: str,
    client: httpx.AsyncClient,
    index: int,
    course_id: str,
    allocation_id: str,
    measurements: dict[str, list[float]],
    errors: Counter,
    gate: asyncio.Semaphore,
    start_barrier: asyncio.Barrier,
    authenticated_at: float,
    trace_events: list[str],
    connection_observations: Counter,
    failure_details: list[str],
) -> None:
    name, path = request_for(role, index, course_id, allocation_id)
    await start_barrier.wait()
    started = time.perf_counter()
    measurements["session_age_at_read"].append(started - authenticated_at)
    async with gate:
        tcp_connects_before = trace_events.count("httpcore.connection.connect_tcp.started")
        trace_offset = len(trace_events)
        try:
            response = await client.get(path)
            response.raise_for_status()
            validate_payload(name, response.json())
            measurements[name].append(time.perf_counter() - started)
        except Exception as error:
            errors[f"{name}_{error_label(error)}"] += 1
            trace_window = trace_events[trace_offset:]
            detail = str(error)[:160] if isinstance(error, httpx.RemoteProtocolError) else ""
            failure_details.append(
                f"index={index} role={role} route={name} "
                f"seconds_since_login={started - authenticated_at:.3f} "
                f"error={type(error).__name__} detail={detail!r} trace={trace_window}"
            )
        finally:
            tcp_connects_after = trace_events.count("httpcore.connection.connect_tcp.started")
            observation = (
                "new_tcp" if tcp_connects_after > tcp_connects_before else "reused_connection"
            )
            connection_observations[f"read_{observation}"] += 1
            measurements[f"{name}_end_to_end"].append(time.perf_counter() - started)


async def sample_database(monitor, samples: list[dict[str, int]], done: asyncio.Event) -> None:
    while not done.is_set():
        try:
            samples.append(await asyncio.to_thread(read_database_metrics, monitor))
        except Exception:
            # The next sample may still succeed; record missing samples in the summary.
            pass
        try:
            await asyncio.wait_for(done.wait(), timeout=0.2)
        except TimeoutError:
            continue


async def cleanup_sessions(
    clients: list[tuple[httpx.AsyncClient, list[str]]],
    errors: Counter,
    failure_details: list[str],
    measurements: dict[str, list[float]],
) -> tuple[int, int]:
    gate = asyncio.Semaphore(5)
    results = [0, 0]

    async def logout(index: int, client: httpx.AsyncClient, trace_events: list[str]) -> None:
        started = time.perf_counter()
        try:
            async with gate:
                trace_offset = len(trace_events)
                response = await client.post("/api/auth/logout")
                response.raise_for_status()
                if response.status_code != 204 or response.content:
                    raise ValueError("Logout did not return an empty 204 response")
                results[0] += 1
        except Exception as error:
            results[1] += 1
            errors[f"logout_{error_label(error)}"] += 1
            detail = str(error)[:160] if isinstance(error, httpx.RemoteProtocolError) else ""
            failure_details.append(
                f"index={index} phase=logout error={type(error).__name__} "
                f"detail={detail!r} trace={trace_events[trace_offset:]}"
            )
        finally:
            measurements["logout"].append(time.perf_counter() - started)
            await client.aclose()

    await asyncio.gather(
        *(
            logout(index, client, trace_events)
            for index, (client, trace_events) in enumerate(clients)
        )
    )
    return results[0], results[1]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def print_latency(name: str, values: list[float]) -> None:
    if values:
        print(
            f"latency_{name}_seconds n={len(values)} "
            f"p50={statistics.median(values):.3f} p95={percentile(values, 0.95):.3f} "
            f"p99={percentile(values, 0.99):.3f} max={max(values):.3f}"
        )


async def run(concurrency: int, request_concurrency: int) -> int:
    if len(PASSWORD) < 12:
        raise SystemExit("Set AMS_DEMO_PASSWORD in the local development environment")
    course_id, allocation_id = await bootstrap_ids()
    measurements: dict[str, list[float]] = defaultdict(list)
    errors: Counter = Counter()
    connection_observations: Counter = Counter()
    failure_details: list[str] = []
    samples: list[dict[str, int]] = []
    monitor = make_database_monitor()
    initial_db = await asyncio.to_thread(read_database_metrics, monitor)
    login_gate = asyncio.Semaphore(8)
    setup_started = time.perf_counter()
    sessions = await asyncio.gather(
        *(create_session(i, login_gate, measurements, errors) for i in range(concurrency))
    )
    setup_seconds = time.perf_counter() - setup_started
    active = [(i, item) for i, item in enumerate(sessions) if item]

    sample_done = asyncio.Event()
    sampler = asyncio.create_task(sample_database(monitor, samples, sample_done))
    burst_started = time.perf_counter()
    request_gate = asyncio.Semaphore(request_concurrency)
    start_barrier = asyncio.Barrier(max(1, len(active)))
    await asyncio.gather(
        *(
            measured_request(
                role,
                client,
                index,
                course_id,
                allocation_id,
                measurements,
                errors,
                request_gate,
                start_barrier,
                authenticated_at,
                trace_events,
                connection_observations,
                failure_details,
            )
            for index, (role, client, authenticated_at, trace_events) in active
        )
    )
    burst_seconds = time.perf_counter() - burst_started
    sample_done.set()
    await sampler
    logouts_ok, logouts_failed = await cleanup_sessions(
        [(client, trace_events) for _, (_, client, _, trace_events) in active],
        errors,
        failure_details,
        measurements,
    )
    peak_connections = max(
        [initial_db["connections"], *(sample["connections"] for sample in samples)]
    )
    peak_active = max(
        [initial_db["active_connections"], *(sample["active_connections"] for sample in samples)]
    )
    route_names = {
        "dashboard",
        "history",
        "recovery",
        "defaulters",
        "analytics",
        "admin_dashboard",
    }
    successful_reads = sum(len(measurements[name]) for name in route_names)
    total_reads = sum(len(measurements[f"{name}_end_to_end"]) for name in route_names)
    failed_reads = sum(
        value for key, value in errors.items() if not key.startswith(("login_", "logout_"))
    )
    api_pool = application_engine.pool
    print(
        f"environment=local-compose concurrency_requested={concurrency} "
        f"authenticated_sessions={len(active)} unique_seeded_accounts=8 "
        f"client_request_fanout={request_concurrency} "
        f"role_mix=student_70pct_faculty_20pct_admin_10pct "
        f"workload=one_read_per_session_then_bounded_logout "
        f"db_max_connections={initial_db['max_connections']} "
        f"db_connections_before={initial_db['connections']} "
        f"db_connections_peak={peak_connections} db_connections_sampled={len(samples)} "
        f"db_active_connections_peak={peak_active} "
        f"database_bytes={initial_db['database_bytes']} "
        f"users_in_db={initial_db['users']} attendance_rows_in_db={initial_db['attendance_rows']} "
        f"api_pool_size={api_pool.size()} api_max_overflow={api_pool._max_overflow} "
        f"api_http_request_concurrency={settings.http_request_concurrency}"
    )
    print(
        f"setup_seconds={setup_seconds:.2f} read_burst_seconds={burst_seconds:.2f} "
        f"read_requests_total={total_reads} read_requests_success={successful_reads} "
        f"read_requests_failed={failed_reads} "
        f"http_timeouts={sum(v for k, v in errors.items() if 'timeout' in k)} "
        f"database_pool_errors={sum(v for k, v in errors.items() if 'database_pool_error' in k)} "
        f"logout_success={logouts_ok} logout_failed={logouts_failed} "
        f"total_errors={sum(errors.values())}"
    )
    print("connection_observations=" + str(dict(connection_observations)))
    trace_counts = Counter(event for _, (_, _, _, trace_events) in active for event in trace_events)
    print(
        "httpcore_trace="
        + str(
            {
                key: value
                for key, value in trace_counts.items()
                if "connect_tcp" in key or "receive_response_headers" in key
            }
        )
    )
    for name, values in sorted(measurements.items()):
        print_latency(name, values)
    print_latency(
        "read_success",
        [value for name in route_names for value in measurements[name]],
    )
    print_latency(
        "read_end_to_end",
        [value for name in route_names for value in measurements[f"{name}_end_to_end"]],
    )
    print("error_categories=" + (str(dict(errors)) if errors else "none"))
    for detail in failure_details:
        print("request_failure=" + detail)
    monitor.dispose()
    return 1 if errors or logouts_failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=100)
    parser.add_argument("--request-concurrency", type=int, default=15)
    options = parser.parse_args()
    if options.concurrency < 1 or options.concurrency > 1000:
        raise SystemExit("--concurrency must be between 1 and 1000")
    if options.request_concurrency < 1 or options.request_concurrency > 1000:
        raise SystemExit("--request-concurrency must be between 1 and 1000")
    raise SystemExit(asyncio.run(run(options.concurrency, options.request_concurrency)))

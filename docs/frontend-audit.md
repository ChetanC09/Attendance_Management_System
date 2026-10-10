# Frontend Audit and Integration Status

The System Design Document and Implementation Plan define the product and API contracts. The Solaris Hybrid Editorial reference defines the visual direction. The provided frontend remains a Vite/React application; it is integrated to the existing FastAPI/PostgreSQL backend rather than replaced.

## Completed

- Applied the Solaris palette (`#FF5722`, `#131518`, `#FF8A65`, `#FFF5F2`), Plus Jakarta Sans, JetBrains Mono, warm neutral surfaces, focus states, reduced-motion behavior, and responsive role-scoped navigation.
- Replaced role-preview access with cookie-session login, `/api/auth/me` restoration, logout, password change, forgot-password, and reset-password flows. Role comes from the server. UI role guards complement backend authorization.
- Made route state URL-backed under `/app/{route}` with browser back/forward support. Reset-password links use the token query emitted by the backend.
- Connected student dashboards, attendance summaries/history, recovery and projection calculations, recurring timetable, requests and optional supporting documents, notifications/preferences, and section announcements to authenticated APIs.
- Connected faculty today's lectures, recurring schedule, attendance sessions, authorized roster, manual attendance corrections with reasons, explicit camera frame recognition, request decisions, defaulter analytics, and course announcements.
- Added the faculty attendance WebSocket subscription; the live session state reports whether updates are connected, refreshes the roster on attendance events, and responds to session closure.
- Added capped exponential reconnect/backoff for dropped faculty attendance WebSocket connections, with roster-refresh failures surfaced in the UI.
- Made request-detail URLs include the request ID so student request links survive refresh and can be shared/deep-linked; parsed the detail route separately from the ID.
- Render structured API validation details as readable JSON instead of `[object Object]`.
- Expanded faculty analytics with labeled course/section allocations and per-lecture attendance trends; faculty dashboard class rows now include course and room labels.
- Added student course-specific attendance history navigation using the backend's `course_id` filter.
- Replaced admin previews with live account creation/profile/status management, department/year/semester/section/course/allocation/classroom/timetable CRUD, lecture generation/cancellation/rescheduling, attendance and notification settings, and audit log retrieval. Foreign-key fields accept record UUIDs because the current backend contracts expose IDs rather than joined selectors.
- Connected the administrator user-directory route to its real user CRUD screen and removed stale “integration pending” messaging from the academic-directory hub.
- Added a student-scoped attendance-threshold endpoint so student dashboards and course views read the configured value without calling an admin-only API.
- Added an administrator operational overview for scheduled lectures, attendance records/rate, pending requests, open sessions, and low-attendance student-course records.
- Added backend contracts for student/faculty timetable views, session roster, and allocation-scoped announcements, including migration `0003_course_announcements`.
- Removed fictional recognition/success states, unsupported policy/hardware claims, and stale sample flows from reachable screens.

## Validation

- Fresh local verification on 2026-10-10: `npm run lint` and `npm run build` pass after dependency remediation. The production build emitted a 354.76 kB JavaScript bundle (96.24 kB gzip). `npm audit` reports zero vulnerabilities.
- Backend: 32 unit and integration tests pass against `/srv/ams` in the rebuilt local backend container; one Starlette/httpx deprecation warning remains. The normal API image intentionally contains no test tree. `PYTHONPATH=/srv/ams` is used so the container tests import the rebuilt source rather than an installed wheel. `pip-audit` reports no known vulnerabilities in installed PyPI packages; it skips the local `ams-backend` project because the package is not published to PyPI.
- `ruff check .` and `ruff format --check .` pass on the backend after the current implementation edits; the test file is formatted with Ruff.
- The cross-role journey verifies anonymous rejection, student denial for admin/attendance routes, two authorized WebSocket connections receiving the same attendance event, session closure delivery, request approval, recalculated student attendance, and audit payload persistence.
- Docker Compose startup succeeded after creating an ignored local development `.env`. PostgreSQL, API readiness, and worker were healthy; Alembic is at `0003_course_announcements`.
- Before browser testing, the development seeder completed three consecutive invocations; seed-only PostgreSQL counts remained stable at 8 users, 1 department, 1 academic year, 1 semester, 1 section, 3 courses, 3 allocations, 43 lectures, 216 attendance rows, 1 request, 1 announcement, and 1 notification.
- The read-only authenticated API smoke script passed 24 checks covering admin, faculty, and student routes, role isolation, and invalid-origin rejection.
- The read-only authenticated API smoke script passes 24 checks after the browser journeys, against the rebuilt runtime. `git diff --check` passes after the documentation updates.
- Security regression coverage now includes production-secret rejection, one-time password-reset/session revocation, production cookie flags, upload content signatures and access control, safe S3 error mapping, and sanitized worker failure persistence. Storage/vision adapter unit tests use fakes; they do not establish real provider or inference operation.
- Clean migration upgrade and populated restore checks passed in disposable PostgreSQL databases. `pg_dump`/`pg_restore` reproduced the active local DB's 9 users and 223 attendance rows; a downgrade to `0002_academic_attendance_domains` and upgrade back to `0003_course_announcements` succeeded. Temporary databases and dump were removed.
- The synchronized probe validates each login role/cookie, response JSON shape, and empty-204 logout. An earlier rebuilt-image run on 2026-10-11 completed 97/100 reads and 100/100 logouts; its three read failures were client `RemoteProtocolError` resets, with no HTTP timeouts, DB pool errors, or matching API 5xx/traceback. Investigation traced those resets to Uvicorn's 5-second keep-alive timeout interacting with the barrier and reused idle connections. After the shared entrypoint set keep-alive to 30 seconds, five consecutive probes against the rebuilt image completed 100/100 valid reads and logouts; per-run latency and pool evidence is recorded in `integration/README.md`. API concurrency remains capped at 15 with a 5+10 SQLAlchemy pool; sampled PostgreSQL peak was 17 connections, with about 11 MB of local data, 223 attendance rows, and eight seeded principals. This tests concurrent cookie sessions, not 100 distinct users or production capacity. An earlier unbounded spike saturated the pool and motivated the concurrency bound and retryable 503 fallback.
- Browser responsive checks on the login page at 375px and 714px reported document widths equal to the viewport. Earlier manual cross-role journeys remain as documented below; accessibility and all role screens at additional breakpoints are not yet fully audited.

## Browser verification (2026-10-10)

- Ran the local app in the in-app browser against the Compose API/PostgreSQL stack and logged in as admin, faculty, and student using local demo accounts.
- Student: opened the attendance dashboard/history, submitted a regularization request, opened its ID-bearing detail URL directly, and refreshed it. The request ID, PENDING status, and server-backed reason survived refresh.
- Faculty: approved that synthetic request. The queue changed to APPROVED; the student dashboard changed from 67.4% (29/43) to 69.8% (30/43), then to 70.5% (31/44) after the manual session. Student notifications showed “Your regularization request was approved.”
- Faculty: used the admin browser UI to create a Saturday timetable entry and dated lecture in the local dev DB, opened a manual attendance session, saved a mark for the synthetic student, and closed the session. The roster showed one present and six absent; the student dashboard showed the resulting 31/44 attendance total. The audit view showed session OPEN/CLOSE records; this browser mark was made before the manual-mark audit fix below.
- Admin: opened dashboard, user directory, academic structure, departments, courses, timetable, governance/settings, and audit routes. Created, deactivated, and reactivated a disposable browser-QA account; it is now inactive. The test timetable entry, generated lecture, request, attendance marks, and notifications remain in the local development database as synthetic test data.
- After browser testing, nine additional seeder invocations left aggregate counts unchanged: 9 users (the browser-QA account is inactive), 1 department, 1 academic year, 1 semester, 1 section, 3 courses, 3 allocations, 4 timetable entries, 44 lectures, 223 attendance rows, 2 requests, 1 announcement, and 2 notifications. Existing demo-account password hashes now sync to the configured local `AMS_DEMO_PASSWORD` on each seed.
- Audit review found that newly created attendance marks were not audited. `record_attendance` now records actor, target student/lecture/session, status, source, reason, and attendance ID in the same transaction; the new unit regression test passes. Existing pre-fix browser marks do not gain retroactive audit rows.
- At the browser's 714px viewport, fixed horizontal overflow in the admin lecture generator (document width now fits the viewport). Login page also fits at 375px and 714px. Keyboard-only accessibility, camera permission states, browser reconnect/backoff, and real vision inference were not verified. Two authenticated WebSocket clients do receive attendance and closure events in the backend integration test.

## Route and requirement matrix

| Journey | Implementation | Browser evidence | Remaining verification |
|---|---|---|---|
| Authentication and role navigation | Implemented | Admin, faculty, student login/logout; role-specific navigation | Password reset email provider and production cross-origin cookies |
| Admin accounts and academic operations | Implemented | Directory lifecycle; academic, department, course, timetable, settings, audit routes; synthetic timetable create/generate | Full validation/conflict/permission matrix and every update operation |
| Student attendance and requests | Implemented | Totals, history, request create/detail/reload, approval outcome, notification | Recovery planner math, preferences/profile persistence, document upload/download |
| Faculty attendance and decisions | Implemented | Manual session/mark, close/auto-absence, request approval, student refresh; two authenticated WebSocket clients receive the same attendance and closure events in integration tests; creation audit payload persisted | Browser reconnect, camera-permission states, live vision inference |
| Responsive/accessibility | Partial | Login viewport has no horizontal overflow at 375px/714px; admin generator fix at 714px | Full role-route review, keyboard-only pass, contrast and screen-reader checks |

## Local startup

- Root `.env` was generated from `.env.example` with a container-correct database URL, random development secret, and generated development demo password. `.env` is ignored by Git. The demo admin login is `admin@ams.dev`; its password is stored in `.env` as `AMS_DEMO_PASSWORD`. The local bootstrap-admin path was not configured or exercised.
- Rebuild/start the API after the latest backend edits with `docker compose up -d --build`; Docker Desktop must be running and accessible. Start the frontend with `cd frontend && npm run dev`.
- Development demo accounts and academic/attendance fixtures are created with `docker compose exec -e AMS_SEED_DEMO=true backend python -m scripts.seed_demo`; credentials are documented in `docs/deployment.md`. Camera recognition additionally requires the optional vision dependencies and an enrolled, consenting face profile; manual attendance remains available.

## Remaining constraints

- Architecture decision for this scope: retain the supplied Vite/React frontend to support the owner's current Vercel work and avoid an unrequested framework migration. This remains an explicit deviation from the Next.js design; owner sign-off or a separate migration proposal is still required if strict conformance is a release gate.
- The latest backend additions (`/api/admin/overview`, faculty allocation/trend analytics, and CORS `PUT` support) compile, pass the unit suite, and have been rebuilt. The admin overview received an authenticated runtime smoke check.
- WebSocket delivery was exercised with two authenticated test clients. Browser reconnect/backoff and server restart recovery remain unverified.
- The local development database now contains the idempotent demo fixtures described in `deployment.md`; these are synthetic development data, not institution-provided academic records. Production remains unseeded by `seed_demo.py`. Add/reset disposable fixtures before full browser journey testing.
- Removed mock-backed context actions and the two unreachable mock-only roster components. `frontend/src/data/mockData.ts` remains in the repository, but the current router has no imports of it; continue the route/deep-link audit before claiming every design journey is complete.
- SMTP and Twilio are not configured in the local environment. Password-reset email and external notification delivery therefore require provider configuration.
- Camera recognition depends on optional InsightFace/OpenCV runtime packages and face enrollment. The frontend submits actual frames only after an explicit capture action and reports backend recognition states.

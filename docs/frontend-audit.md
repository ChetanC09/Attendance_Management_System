# Frontend Audit and Integration Status

The System Design Document and Implementation Plan define the product and API contracts. The Solaris Hybrid Editorial reference defines the visual direction. The provided frontend remains a Vite/React application; it is integrated to the existing FastAPI/PostgreSQL backend rather than replaced.

## Completed

- Applied the Solaris palette (`#FF5722`, `#131518`, `#FF8A65`, `#FFF5F2`), Plus Jakarta Sans, JetBrains Mono, warm neutral surfaces, focus states, reduced-motion behavior, and responsive role-scoped navigation.
- Replaced role-preview access with cookie-session login, `/api/auth/me` restoration, logout, password change, forgot-password, and reset-password flows. Role comes from the server. UI role guards complement backend authorization.
- Made route state URL-backed under `/app/{route}` with browser back/forward support. Reset-password links use the token query emitted by the backend.
- Connected student dashboards, attendance summaries/history, recovery and projection calculations, recurring timetable, requests and optional supporting documents, notifications/preferences, and section announcements to authenticated APIs.
- Connected faculty today's lectures, recurring schedule, attendance sessions, authorized roster, manual attendance corrections with reasons, explicit camera frame recognition, request decisions, defaulter analytics, and course announcements.
- Added the faculty attendance WebSocket subscription; the live session state reports whether updates are connected, refreshes the roster on attendance events, and responds to session closure.
- Expanded faculty analytics with labeled course/section allocations and per-lecture attendance trends; faculty dashboard class rows now include course and room labels.
- Added student course-specific attendance history navigation using the backend's `course_id` filter.
- Replaced admin previews with live account creation/profile/status management, department/year/semester/section/course/allocation/classroom/timetable CRUD, lecture generation/cancellation/rescheduling, attendance and notification settings, and audit log retrieval. Foreign-key fields accept record UUIDs because the current backend contracts expose IDs rather than joined selectors.
- Connected the administrator user-directory route to its real user CRUD screen and removed stale “integration pending” messaging from the academic-directory hub.
- Added a student-scoped attendance-threshold endpoint so student dashboards and course views read the configured value without calling an admin-only API.
- Added an administrator operational overview for scheduled lectures, attendance records/rate, pending requests, open sessions, and low-attendance student-course records.
- Added backend contracts for student/faculty timetable views, session roster, and allocation-scoped announcements, including migration `0003_course_announcements`.
- Removed fictional recognition/success states, unsupported policy/hardware claims, and stale sample flows from reachable screens.

## Validation

- Frontend: `npm run lint` and `npm run build` pass. Browser smoke checks passed the admin overview and user directory, student overview/course attendance/recovery/timetable/requests/request details/notifications/settings, and faculty overview/timetable/attendance setup/analytics/request review/announcements/settings against seeded API data.
- Backend: Python compilation passes; all 17 backend unit and integration tests pass in the Docker test container.
- Docker Compose rebuilt successfully; database and backend are healthy and the worker is running. Alembic is at `0003_course_announcements`.
- Read-only authenticated API smoke checks cover 24 admin/faculty/student routes, role isolation, and invalid-origin rejection. The database seeder was run twice to verify idempotence.
- `git diff --check` passes. Solaris styling and populated screen hierarchy were visually checked on the admin dashboard. Camera permission and real vision inference were not exercised.

## Local startup

- Root `.env` was generated from `.env.example` with a container-correct database URL, random development secret, and a local bootstrap administrator. `.env` is ignored by Git. The login is `admin@ams.dev`; the generated password is stored in the root `.env` as `AMS_BOOTSTRAP_ADMIN_PASSWORD`.
- Rebuild/start the API after the latest backend edits with `docker compose up -d --build`; Docker Desktop must be running and accessible. Start the frontend with `cd frontend && npm run dev`.
- Development demo accounts and academic/attendance fixtures are created with `python -m scripts.seed_demo`; credentials are documented in `docs/deployment.md`. Camera recognition additionally requires the optional vision dependencies and an enrolled, consenting face profile; manual attendance remains available.

## Remaining constraints

- The frontend repository supplied was Vite/React, while the architecture document names Next.js. This work added stable browser URLs without replacing the supplied app stack. If strict Next.js conformance is required, migrate the Vite shell and build pipeline as a separate planned change.
- The latest backend additions (`/api/admin/overview`, faculty allocation/trend analytics, and CORS `PUT` support) compile, pass the unit suite, and have been rebuilt. The admin overview received an authenticated runtime smoke check.
- The current UI uses a regular WebSocket connection for session events, but connection recovery/reconnect behavior and multi-client event delivery still need an end-to-end runtime check.
- No real academic seed records or student/faculty accounts were provided. Pages correctly render empty states until administrators add departments, academic periods, sections, courses, allocations, timetable entries, and user accounts. Add disposable student/faculty fixtures before full browser journey testing.
- SMTP and Twilio are not configured in the local environment. Password-reset email and external notification delivery therefore require provider configuration.
- Camera recognition depends on optional InsightFace/OpenCV runtime packages and face enrollment. The frontend submits actual frames only after an explicit capture action and reports backend recognition states.

# AMS API Contract (Backend Baseline)

API prefix: `/api`. JSON requests/responses use Pydantic validation. Authentication is an `ams_session` HttpOnly cookie issued by login; browser clients must send credentials. `GET /health` is a liveness check and `GET /health/ready` checks PostgreSQL. FastAPI serves `/docs`, `/redoc`, and `/openapi.json`.

## Authentication

| Method | Path | Access |
|---|---|---|
| POST | `/api/auth/login` | Public; email/password; returns user and expiry, sets cookie |
| POST | `/api/auth/logout` | Public; revokes current cookie session |
| GET | `/api/auth/me` | Authenticated |
| POST | `/api/auth/change-password` | Authenticated; current and new password |
| POST | `/api/auth/forgot-password` | Public; anti-enumeration response; SMTP delivery configured by environment |
| POST | `/api/auth/reset-password` | Public; one-time token and new password |

## Academic administration (ADMIN)

| Method | Path | Purpose |
|---|---|---|
| GET/POST/PATCH | `/api/admin/departments[/{id}]` | Departments |
| GET/POST/PATCH | `/api/admin/academic-years[/{id}]` | Academic years |
| GET/POST/PATCH | `/api/admin/semesters[/{id}]` | Semesters |
| GET/POST/PATCH | `/api/admin/sections[/{id}]` | Sections |
| GET/POST/PATCH | `/api/admin/courses[/{id}]` | Courses |
| GET/POST/PATCH | `/api/admin/classrooms[/{id}]` | Classrooms |
| GET/POST/PATCH | `/api/admin/allocations[/{id}]` | Faculty/course/section allocations |
| GET/POST/PATCH | `/api/admin/timetable[/{id}]` | Recurring timetable entries |
| POST | `/api/admin/timetable/{entry_id}/generate?through=DATE` | Generate dated lectures |
| GET | `/api/admin/lectures` | Lecture listing; supports `starts_after`, `starts_before` |
| POST | `/api/admin/lectures/{id}/cancel` | Cancel a scheduled lecture with reason |
| PATCH | `/api/admin/lectures/{id}/reschedule` | Change scheduled lecture time/classroom |
| GET/POST/PATCH | `/api/admin/users[/{id}]` | Account list/create/status/profile update |
| GET/PUT | `/api/admin/settings/attendance-threshold` | Attendance threshold |
| GET/PUT | `/api/admin/settings/notifications` | Enable configured SMTP/Twilio delivery channels |
| GET | `/api/admin/audit-logs` | Filterable audit history |

## Faculty

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/faculty/timetable` | Authorized recurring schedule |
| GET | `/api/faculty/lectures/today` | Today's assigned lectures |
| POST | `/api/faculty/attendance/session` | Open a lecture attendance session |
| GET | `/api/faculty/attendance/session/{id}` | Session and marks |
| POST | `/api/faculty/attendance/manual` | Mark a student in the active section |
| PATCH | `/api/faculty/attendance/{id}` | Correct a mark; reason required |
| POST | `/api/faculty/attendance/session/{id}/close` | Close and mark unmarked roster entries absent |
| POST | `/api/faculty/attendance/session/{id}/recognize` | Submit one JPEG/PNG frame for recognition and attendance decision |
| GET | `/api/faculty/analytics/defaulters?allocation_id=UUID&threshold=75` | Authorized allocation defaulters |
| GET | `/api/faculty/requests` | Assigned requests |
| POST | `/api/faculty/requests/{id}/approve` | Approve (regularization is transactional) |
| POST | `/api/faculty/requests/{id}/reject` | Reject; reason required |
| GET | `/api/faculty/requests/{id}` | Assigned request details |
| GET | `/api/faculty/requests/{id}/documents` | List supporting document metadata |
| GET | `/api/faculty/requests/documents/{id}` | Download assigned request document |

## Student

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/student/attendance` | Course attendance summaries; optional `course_id` |
| GET | `/api/student/attendance/history` | Paginated history (`limit`, `offset`) |
| GET | `/api/student/analytics/recovery?course_id=UUID&target_percentage=75` | Recovery plan |
| GET | `/api/student/analytics/projection?course_id=UUID&potential_absences=1` | Predictive attendance risk |
| POST/GET | `/api/student/requests` | Create/list own leave or regularization requests |
| GET | `/api/student/requests/{id}` | Own request status |
| POST | `/api/student/requests/{id}/documents` | Upload PDF, PNG, JPEG (configured size limit) |
| GET | `/api/student/requests/{id}/documents` | List own supporting document metadata |
| GET | `/api/student/requests/documents/{id}` | Download own document |
| GET | `/api/notifications` | In-app notifications for any authenticated role |
| POST | `/api/notifications/{id}/read` | Mark own notification read |
| GET | `/api/notifications/preferences` | Read own channel preferences |
| PUT | `/api/notifications/preferences/{channel}?enabled=true` | Set own channel preference |
| POST/DELETE | `/api/student/face-profile/enroll` and `/api/student/face-profile` | Consent-based enrollment / revocation |

## WebSocket

`/ws/attendance/{session_id}` authenticates with the same cookie and requires the assigned faculty member. Server events include `SESSION_STARTED`, `ATTENDANCE_RECORDED`, and `SESSION_CLOSED`. `PING` receives `PONG`; image frames go through the HTTP recognition endpoint. Unsupported WebSocket event types receive `ERROR`.

## Common errors

- `401`: missing/invalid/expired session or invalid credentials.
- `403`: role or resource scope denied.
- `404`: resource does not exist or is outside the caller's visibility.
- `409`: duplicate/conflicting state or database uniqueness conflict.
- `413` / `415`: document/frame size or type rejected.
- `422`: request validation or business rule rejected.
- `423`: account temporarily locked.
- `503`: optional vision dependencies are unavailable.

All permission checks are enforced by the API. Lists use bounded limits where applicable. This document tracks the current backend baseline; update it with each endpoint contract change.

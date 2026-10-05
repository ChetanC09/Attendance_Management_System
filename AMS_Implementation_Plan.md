# Attendance Management System (AMS)
## Full Implementation Plan — Frontend / Backend / Integration

**Primary implementation tool:** Codex  
**Frontend design tools:** Stitch + Google AI Studio  
**Repository structure:** Locked to the System Design Document  
**Current execution target:** Backend-first implementation

---

# 1. Execution Strategy

The project is split into exactly three implementation tracks:

```text
TRACK 1 — FRONTEND
Tanuj + Stitch + Google AI Studio

TRACK 2 — BACKEND
Codex

TRACK 3 — INTEGRATION
Codex
```

The three tracks converge at the API and end-to-end behavior boundary.

For the current Codex execution:

> **Backend Track starts now.**
>
> The `frontend/` folder will be supplied by Tanuj soon.
>
> Codex must build the backend and supporting infrastructure without waiting for the frontend and must not generate a replacement frontend.

---

# 2. Locked Repository Structure

```text
attendance-management-system/
│
├── frontend/                       # Tanuj supplies later
│
├── backend/                        # Track 2
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth/
│   │   │   ├── student/
│   │   │   ├── faculty/
│   │   │   ├── admin/
│   │   │   ├── attendance/
│   │   │   ├── timetable/
│   │   │   ├── analytics/
│   │   │   ├── exceptions/
│   │   │   └── notifications/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── vision/
│   │   ├── workers/
│   │   ├── dependencies/
│   │   └── main.py
│   │
│   ├── migrations/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   ├── scripts/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── README.md
│
├── integration/                    # Track 3
│   ├── contracts/
│   ├── e2e/
│   ├── fixtures/
│   ├── scripts/
│   └── README.md
│
├── docs/
│   ├── system-design.md
│   ├── implementation-plan.md
│   └── api-contract.md
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

Do not redesign this directory structure during implementation without an explicit architecture change.

---

# 3. Track Ownership

## Track 1 — Frontend

Owner:
- Tanuj

Tools:
- Stitch
- Google AI Studio
- Next.js/React/TypeScript

Output:
```text
frontend/
```

Frontend will be inserted into the repository after the Stitch → Google AI Studio process.

---

## Track 2 — Backend

Owner:
- Codex

Includes everything required for the actual server-side product:

- FastAPI
- database
- migrations
- models
- repositories
- business logic
- authentication
- RBAC
- attendance
- vision
- analytics
- exceptions
- notifications
- background workers
- tests
- Docker
- configuration
- backend documentation

---

## Track 3 — Integration

Owner:
- Codex

Includes:

- API contracts
- frontend/backend integration
- E2E tests
- browser/API workflows
- live attendance integration
- error/permission verification
- integration fixtures/scripts

Integration begins progressively, but final integration happens after Tanuj provides `frontend/`.

---

# 4. TRACK 2 — BACKEND IMPLEMENTATION

# Phase B0 — Repository and Environment Foundation

## Tasks

Create:

```text
backend/
integration/
docs/
```

Do not implement `frontend/`.

Set up:

- Python project
- FastAPI
- PostgreSQL connection
- SQLAlchemy
- Alembic
- Pydantic settings
- structured logging
- environment management
- Docker
- test framework

Root:

```text
docker-compose.yml
.env.example
.gitignore
README.md
```

Backend:

```text
pyproject.toml
Dockerfile
README.md
```

## Acceptance criteria

- backend starts
- `/health` works
- PostgreSQL connection verified
- migration system initialized
- test runner works
- Docker Compose starts required infrastructure

---

# Phase B1 — Database Foundation

Implement SQLAlchemy models and Alembic migrations for:

```text
users
student_profiles
faculty_profiles
departments
academic_years
semesters
sections
courses
course_allocations
classrooms
timetable_entries
lectures
attendance
face_profiles
face_embeddings
leave_requests
supporting_documents
notifications
notification_preferences
audit_logs
```

## Required database constraints

At minimum:

- unique institutional IDs
- valid foreign keys
- course-code uniqueness within applicable academic context
- unique attendance per student/lecture
- valid role values
- active/inactive states
- request-status constraints

## Acceptance criteria

- clean database migration from zero
- rollback works
- seed data mechanism exists
- constraints are enforced by the DB, not only application code

---

# Phase B2 — Authentication

Implement:

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
POST /api/auth/change-password
POST /api/auth/forgot-password
POST /api/auth/reset-password
```

Implement:

- password hashing with Argon2id
- secure session/token handling
- HttpOnly cookie strategy
- session expiry
- failed-login tracking
- account locking
- logout invalidation strategy

## Acceptance criteria

- valid login succeeds
- invalid login fails correctly
- deactivated user cannot login
- lock threshold works
- session expiry works
- `/me` correctly resolves identity and role

---

# Phase B3 — RBAC and Authorization

Implement reusable authorization dependencies.

Example:

```text
require_authenticated_user()
require_role(ADMIN)
require_role(FACULTY)
require_role(STUDENT)
require_course_access()
require_section_access()
```

Authorization must occur server-side.

## Acceptance criteria

- student cannot modify attendance
- faculty cannot access unrelated course attendance
- faculty cannot approve unrelated requests
- student cannot access admin endpoints
- direct API calls are protected

---

# Phase B4 — Academic Management

Implement services and APIs for:

```text
Departments
Academic Years
Semesters
Sections
Courses
Course Allocations
Classrooms
```

Admin APIs:

```text
GET/POST/PATCH
```

with correct authorization.

## Validation

- duplicate identifiers rejected
- inactive academic entities handled correctly
- invalid faculty-course assignments rejected
- duplicate allocation prevented

## Acceptance criteria

Admin can completely create the academic structure required to support attendance.

---

# Phase B5 — Timetable and Lecture Management

Implement:

- timetable creation
- recurring schedules
- lecture generation
- lecture cancellation
- rescheduling
- classroom conflict detection
- faculty conflict detection

## Acceptance criteria

The backend must reject:

```text
same classroom + overlapping time
same faculty + overlapping time
invalid course/faculty/section allocation
```

and must update affected lecture state correctly.

---

# Phase B6 — Core Attendance Engine

Implement attendance domain first without camera integration.

Services:

```text
create_attendance_session()
validate_lecture()
record_attendance()
prevent_duplicate()
modify_attendance()
close_attendance_session()
```

APIs:

```text
POST /api/faculty/attendance/session
GET  /api/faculty/attendance/session/{id}
POST /api/faculty/attendance/manual
PATCH /api/faculty/attendance/{id}
POST /api/faculty/attendance/session/{id}/close
```

## Critical rules

- only authorized faculty
- valid scheduled lecture
- one status per student/lecture
- reason for manual modification
- audit entry for modification

## Acceptance criteria

The complete `MarkAttendance` backend workflow works using manual input before vision integration begins.

---

# Phase B7 — Vision / Facial Recognition

Implement a replaceable vision service boundary.

Suggested structure:

```text
backend/app/vision/
├── detector.py
├── recognizer.py
├── embeddings.py
├── matcher.py
├── service.py
└── schemas.py
```

The exact recognition implementation may sit behind:

```text
VisionService
```

so it can be replaced without changing attendance business logic.

## Required operations

```text
detect_faces()
generate_embedding()
match_identity()
verify_confidence()
```

## Enrollment

Implement backend support for:

- student face profile
- embedding generation
- secure storage/association

## Recognition

Flow:

```text
frame
 ↓
detect
 ↓
embedding
 ↓
match
 ↓
confidence
 ↓
student identity
```

## Acceptance criteria

Vision service returns explicit states:

```text
recognized
unknown
multiple_faces
low_confidence
error
```

It never directly writes attendance.

The Attendance Service makes the final attendance decision.

---

# Phase B8 — Live Attendance Session API

Implement WebSocket support where appropriate:

```text
/ws/attendance/{session_id}
```

Events should be typed.

Example:

```text
SESSION_STARTED
PROCESSING
FACE_DETECTED
STUDENT_RECOGNIZED
UNKNOWN_FACE
MULTIPLE_FACES
ATTENDANCE_RECORDED
DUPLICATE
ERROR
SESSION_CLOSED
```

## Acceptance criteria

A browser or test client can:

1. start a session
2. submit/process recognition events
3. receive status events
4. see attendance counts update
5. close the session

---

# Phase B9 — Analytics

Implement services:

```text
calculate_course_attendance()
calculate_overall_attendance()
get_attendance_history()
generate_defaulter_list()
calculate_recovery_plan()
calculate_projected_attendance()
generate_predictive_alert()
```

## Recovery formula

```text
(P + x)/(C + x) >= T
```

Return:

```text
current_percentage
target_percentage
required_lectures
projected_percentage
achievable
```

## Acceptance criteria

Calculations are deterministic, unit-tested and independent of frontend code.

---

# Phase B10 — Exception Management

Implement:

```text
create_leave_request()
create_regularization_request()
upload_document_metadata()
review_request()
approve_request()
reject_request()
apply_regularization()
get_request_status()
```

APIs should cover:

```text
POST /api/student/requests
GET  /api/student/requests
GET  /api/student/requests/{id}

GET  /api/faculty/requests
GET  /api/faculty/requests/{id}
POST /api/faculty/requests/{id}/approve
POST /api/faculty/requests/{id}/reject
```

Approval must be transactional:

```text
request status update
+
attendance regularization
+
audit entry
```

and then enqueue notification.

---

# Phase B11 — Document Storage

Implement adapter interface:

```text
StorageService
```

Operations:

```text
upload()
download()
delete()
get_metadata()
```

Validate:

- size
- extension
- content type

Store metadata in PostgreSQL.

---

# Phase B12 — Notifications

Implement domain-level notification creation plus worker.

Architecture:

```text
NotificationService
        ↓
NotificationJob
        ↓
Worker
        ├── In-app adapter
        ├── Email adapter
        └── SMS adapter
```

Implement:

- notification creation
- delivery state
- retry
- failed delivery logging
- notification preferences

Notification delivery must never make attendance/leave transactions fail.

---

# Phase B13 — Admin Operations and Audit

Implement:

- user management
- user status
- configuration
- attendance threshold
- notification configuration
- audit log retrieval

Audit every high-value mutation.

---

# Phase B14 — Backend Testing

## Unit tests

At minimum:

- auth
- password hashing
- RBAC
- attendance percentage
- recovery planner
- projected attendance
- defaulter calculation
- timetable conflicts
- duplicate attendance prevention
- regularization rules

## Integration tests

At minimum:

```text
login → authenticated API
admin → create user
admin → create course
faculty → create timetable
faculty → start attendance
faculty → mark attendance
student → view attendance
student → create request
faculty → approve request
notification → queued
audit → recorded
```

---

# Phase B15 — Backend Quality Pass

Verify:

- type hints
- validation
- logging
- exception handling
- transaction boundaries
- database indexes
- authorization
- no secret leakage
- no duplicated business logic
- no dead modules
- OpenAPI documentation

---

# 5. TRACK 1 — FRONTEND PLAN

Tanuj will create and supply the frontend using:

```text
Stitch
   ↓
Google AI Studio
   ↓
frontend/
```

The frontend should conform to the System Design API architecture.

## Required route families

```text
/auth/*

/student/*
/faculty/*
/admin/*
```

## Student pages

```text
dashboard
attendance
attendance/history
attendance/[courseId]
recovery
timetable
requests
requests/[requestId]
notifications
settings
```

## Faculty pages

```text
dashboard
classes
attendance/[sessionId]
attendance/[sessionId]/manual
analytics
defaulters
requests
requests/[requestId]
announcements
timetable
settings
```

## Admin pages

```text
dashboard
users
students
faculty
departments
academic-years
semesters
sections
courses
allocations
classrooms
timetable
settings
audit-logs
```

## Important frontend requirement

The visual implementation must use the design direction established from the two references:

- light-first
- warm coral/orange accent
- premium SaaS polish
- educational friendliness
- generous whitespace
- restrained card use
- strong typography
- role-specific compositions

The frontend is not considered complete merely because routes exist. It must implement loading, error, empty and interaction states.

---

# 6. TRACK 3 — INTEGRATION PLAN

Integration is not one final step. It happens progressively after stable backend contracts exist.

---

# Phase I0 — API Contract Freeze

Create:

```text
integration/contracts/
```

Document each endpoint:

- method
- path
- auth
- request schema
- response schema
- errors
- pagination
- filters
- role permissions

Create machine-readable OpenAPI-derived artifacts where useful.

---

# Phase I1 — Frontend/Auth Integration

When Tanuj supplies `frontend/`:

Connect:

```text
login
logout
me/session
role routing
session expiration
authorization errors
```

Acceptance:

```text
Student → Student dashboard
Faculty → Faculty dashboard
Admin → Admin dashboard
```

---

# Phase I2 — Student Integration

Connect:

```text
dashboard
attendance
history
subject details
recovery planner
timetable
requests
request details
notifications
settings
```

Test that displayed values come from live backend APIs.

---

# Phase I3 — Faculty Integration

Connect:

```text
dashboard
today's classes
attendance session
live recognition
manual attendance
analytics
defaulters
requests
request decisions
announcements
timetable
```

---

# Phase I4 — Admin Integration

Connect:

```text
dashboard
users
academic structure
courses
allocations
classrooms
timetable
settings
audit logs
```

---

# Phase I5 — Camera / Vision Integration

Browser:

```text
getUserMedia()
```

Flow:

```text
camera
 ↓
attendance session
 ↓
frame/image transport
 ↓
backend vision
 ↓
recognition event
 ↓
attendance event
 ↓
live UI update
```

Handle:

- permission denied
- unavailable camera
- unknown student
- multiple faces
- recognition error
- duplicate
- fallback to manual attendance

---

# Phase I6 — Documents / Notifications

Connect:

```text
request creation
 ↓
document upload
 ↓
faculty review
 ↓
approve/reject
 ↓
notification
 ↓
student status
```

---

# Phase I7 — End-to-End Testing

## E2E Student Scenario

```text
Login
→ dashboard
→ inspect attendance
→ open recovery planner
→ create regularization request
→ upload document
→ view pending state
→ receive decision
→ attendance updates
```

## E2E Faculty Scenario

```text
Login
→ today's classes
→ open current lecture
→ start attendance
→ camera
→ recognition
→ attendance update
→ manually resolve failed recognition
→ close session
→ view analytics
```

## E2E Admin Scenario

```text
Login
→ manage user
→ manage course
→ assign faculty
→ configure threshold
→ inspect audit
```

---

# Phase I8 — Cross-Cutting Security Validation

Verify that frontend visibility and backend authorization agree.

Attempt direct API access as:

```text
student → admin endpoint
student → attendance mutation

faculty → unrelated course
faculty → admin endpoint

inactive user → protected endpoint
```

All unauthorized actions must fail correctly.

---

# Phase I9 — Performance and Reliability

Validate against the SRS targets:

```text
dashboard ≤ 3 sec
login ≤ 3 sec
attendance write ≤ 2 sec
analytics update ≤ 5 sec
history ≤ 3 sec
defaulters ≤ 10 sec
recovery ≤ 2 sec
```

Target at least 100 concurrent authenticated users without exceeding the specified response-time requirements.

---

# 7. Codex Operating Instructions

The following rules apply when Codex starts the backend implementation.

## Rule 1 — Read first

Before writing code, inspect:

1. System Design Document
2. Implementation Plan
3. Existing repository
4. Existing code, if any
5. Existing environment/configuration

Do not blindly create a parallel project.

## Rule 2 — Backend-first

Start with Track 2.

Do not wait for `frontend/`.

## Rule 3 — Frontend placeholder

The `frontend/` folder will be inserted by Tanuj soon.

Do not create a replacement frontend.

Do not redesign the architecture around a generated frontend.

Do not overwrite or delete `frontend/`.

## Rule 4 — Work incrementally

At each phase:

```text
implement
→ test
→ verify
→ document
→ continue
```

Do not generate thousands of untested files in one step.

## Rule 5 — Database first

Business modules should use actual database models and migrations.

Avoid fake in-memory persistence except for isolated unit tests.

## Rule 6 — API contract first

Define stable schemas before integrating UI.

## Rule 7 — Security is backend-enforced

Never assume the frontend protects privileged operations.

## Rule 8 — Preserve domain boundaries

Do not put attendance logic into auth services.

Do not put notification delivery into attendance database handlers.

Do not put vision logic directly into API route functions.

## Rule 9 — Vision is replaceable

Keep the recognition engine behind a service interface.

## Rule 10 — Notifications are asynchronous

Never block core attendance/leave transactions waiting for external notification providers.

---

# 8. Backend Implementation Order

Codex should execute approximately in this order:

```text
1. Environment / repository
2. PostgreSQL
3. SQLAlchemy
4. Alembic
5. Core models
6. Authentication
7. RBAC
8. Academic structure
9. Timetable
10. Core attendance
11. Analytics
12. Exceptions
13. Storage
14. Notifications
15. Vision
16. Live attendance WebSocket
17. Admin/audit
18. Testing
19. Docker/infrastructure refinement
20. Backend quality pass
```

Vision is deliberately integrated after the core attendance engine exists so the business rules are independent of recognition technology.

---

# 9. Integration Order

```text
1. API contracts
2. Auth
3. Student APIs
4. Faculty APIs
5. Admin APIs
6. Documents
7. Notifications
8. Camera
9. Live attendance
10. E2E workflows
11. Security checks
12. Performance
13. final QA
```

---

# 10. Definition of Done

A feature is complete only when:

```text
UI
+
API
+
Database
+
Authorization
+
Validation
+
Business rules
+
Errors
+
Audit where required
+
Notifications where required
+
Tests
```

Example:

`Approve Leave` is complete only if:

```text
faculty can open request
+
faculty is authorized
+
approval is validated
+
request changes state
+
attendance is regularized transactionally
+
audit is created
+
notification is queued
+
student sees updated status
+
tests pass
```

---

# 11. Final Convergence

The three tracks converge as follows:

```text
              ┌───────────────┐
              │   FRONTEND    │
              │ Tanuj / Stitch│
              │ / AI Studio   │
              └───────┬───────┘
                      │
                      │ API Contracts
                      ▼
              ┌───────────────┐
              │    BACKEND    │
              │    Codex      │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │  INTEGRATION  │
              │    Codex      │
              └───────┬───────┘
                      │
                      ▼
                COMPLETE AMS
```

The backend can be implemented and tested before `frontend/` arrives.

Once Tanuj supplies the frontend folder, Track 3 connects it to the already-stable backend contracts.

---

# 12. Immediate Codex Target

The first Codex execution should **not** attempt frontend work.

It should:

```text
READ SYSTEM DESIGN
READ IMPLEMENTATION PLAN
↓
CREATE/VERIFY REPOSITORY STRUCTURE
↓
INITIALIZE BACKEND
↓
INITIALIZE DATABASE + MIGRATIONS
↓
IMPLEMENT AUTH + RBAC
↓
IMPLEMENT ACADEMIC STRUCTURE
↓
IMPLEMENT TIMETABLE
↓
IMPLEMENT CORE ATTENDANCE
↓
TEST EACH STAGE
```

Then proceed through the remaining Backend Track phases.

The `frontend/` folder will be provided by Tanuj later and will be integrated only after the backend contracts are sufficiently stable.

# Attendance Management System (AMS)
## System Design Document — Locked Architecture + Repository Structure

**Institution:** Sardar Patel Institute of Technology  
**Department:** Computer Engineering  
**Project:** Attendance Management System (AMS)  
**Status:** Architecture / implementation baseline  
**Purpose:** Technical source of truth for Codex and the implementation team

---

# 1. Document Role

This document defines **how the complete AMS is engineered**.

It is intentionally different from the visual/UI design work. The UI will be designed separately in Stitch and implemented through Google AI Studio; the resulting frontend will later be placed into the `frontend/` directory defined here.

This document therefore focuses on:

- architecture
- technology choices
- repository structure
- domain boundaries
- database
- APIs
- authentication
- attendance/vision
- analytics
- exceptions
- notifications
- security
- testing
- deployment
- integration contracts

The approved SRS defines AMS as a centralized web application supporting attendance recording, academic scheduling, attendance analytics, leave/regularization, notifications, and management of users and academic structures for Administrator, Faculty, and Student roles. fileciteturn0file3L63-L76

---

# 2. Source Alignment

The implementation must preserve the behavior already established in the SE work.

## 2.1 SRS

The SRS establishes the seven major functional groups:

1. User Authentication & Role-Based Access
2. Smart Attendance Capture
3. Course & Timetable Management
4. Attendance Monitoring & Analytics
5. Attendance Exception Management
6. Notification & Alert System
7. User & Academic Management

fileciteturn0file3L36-L44

## 2.2 Sequence diagrams

Existing SE sequence flows:

- `MarkAttendance`
- `ApproveLeave`
- `ReviewException`

These are core use cases and must remain real implementation flows. fileciteturn0file0L6-L13

## 2.3 Activity diagram

Existing activity flow uses:

- Student
- Faculty
- Admin
- System
- Notification Service

and covers authentication, role dashboards, attendance, notifications, account locking and termination. fileciteturn0file1L8-L15

## 2.4 WBS

The previous WBS divides the project into:

- planning
- requirements
- design
- development
- testing
- deployment
- maintenance

This document is the implementation baseline after design. fileciteturn0file2L12-L19

---

# 3. High-Level Architecture

```text
                         ┌──────────────────────────┐
                         │       Web Browser        │
                         │ Student / Faculty / Admin│
                         └─────────────┬────────────┘
                                       │ HTTPS
                                       ▼
                         ┌──────────────────────────┐
                         │      Next.js Frontend     │
                         │ React + TypeScript        │
                         └─────────────┬────────────┘
                                       │ REST / WebSocket
                                       ▼
                         ┌──────────────────────────┐
                         │       FastAPI Backend     │
                         │                           │
                         │ Auth / RBAC               │
                         │ Academic Management       │
                         │ Attendance                │
                         │ Analytics                │
                         │ Exceptions               │
                         │ Notifications            │
                         │ Administration            │
                         └───────┬──────────┬───────┘
                                 │          │
                         ┌───────▼──────┐ ┌─▼────────────────┐
                         │  PostgreSQL   │ │ Vision Service    │
                         │  Database     │ │ OpenCV            │
                         │              │ │ InsightFace       │
                         └──────────────┘ └──────────────────┘
                                             │
                                   ┌─────────▼──────────┐
                                   │ Background Worker   │
                                   │ Notifications/Jobs  │
                                   └────────────────────┘
```

The SRS already requires client-server architecture, centralized relational data, facial-recognition integration and external notification services. fileciteturn0file3L132-L144

---

# 4. Locked Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js + React + TypeScript |
| Styling | Tailwind CSS |
| UI primitives | shadcn/ui + Radix |
| Server state | TanStack Query |
| Client state | Zustand |
| Forms | React Hook Form + Zod |
| Charts | Recharts |
| Backend | FastAPI + Python |
| API schemas | Pydantic |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Database | PostgreSQL |
| Vector search | pgvector |
| Authentication | JWT / secure session + HttpOnly cookies |
| Password hashing | Argon2id |
| Vision | OpenCV + InsightFace / ArcFace-style recognition |
| API communication | REST |
| Live attendance communication | WebSocket where required |
| File storage | S3-compatible object storage |
| Background jobs | Python worker |
| Testing | Pytest + Playwright |
| Local orchestration | Docker Compose |
| Source of frontend visual design | Stitch |
| Initial frontend implementation/refinement | Google AI Studio |
| Backend + integration implementation | Codex |

The original SRS requires a relational database and leaves the exact facial-recognition engine and database selection as implementation decisions; this document resolves them as above. fileciteturn0file3L48-L53

---

# 5. Fixed Repository / Directory Structure

This structure is **locked**. Do not invent alternative top-level layouts during implementation.

```text
attendance-management-system/
│
├── frontend/
│   └── # CREATED/PLACED BY TANUJ
│
├── backend/
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
│   │   │
│   │   ├── core/
│   │   │   ├── config/
│   │   │   ├── security/
│   │   │   └── logging/
│   │   │
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
│   │
│   ├── scripts/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── README.md
│
├── integration/
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

## Ownership

### `frontend/`
Owned by **Tanuj + Stitch + Google AI Studio**.

Codex must not replace or restructure this folder while implementing the backend.

### `backend/`
Owned by the **Backend Track / Codex**.

Everything required for the API, database, business logic, authentication, vision processing and background workers lives here.

### `integration/`
Owned by the **Integration Track / Codex**.

This contains API contract checks, end-to-end tests, integration fixtures and scripts connecting frontend behavior to backend behavior.

### `docs/`
Shared project documentation.

### Root configuration
`docker-compose.yml`, `.env.example`, `.gitignore`, and the root README support the overall system.

---

# 6. Backend Module Boundaries

The backend follows:

```text
API
 ↓
Service / business logic
 ↓
Repository / data access
 ↓
PostgreSQL
```

Core domains:

```text
Auth
Academic Structure
Timetable
Attendance
Vision
Analytics
Exceptions
Notifications
Administration
Audit
```

No domain should collapse into one giant service file.

---

# 7. Database Design

Core entities:

```text
User
StudentProfile
FacultyProfile
Department
AcademicYear
Semester
Section
Course
CourseAllocation
Classroom
TimetableEntry
Lecture
Attendance
FaceProfile
FaceEmbedding
LeaveRequest
SupportingDocument
Notification
NotificationPreference
AuditLog
```

The SRS ERD already establishes the major entities around users, departments, academic periods, courses, lectures, attendance, leave requests, documents, notifications and logs. fileciteturn0file3L47-L48

Important constraints:

```text
unique institutional identifier
unique course code within academic context
unique(student_id, lecture_id) for attendance
foreign-key integrity
valid academic relationships
```

The SRS explicitly requires relational integrity and duplicate prevention. fileciteturn0file3L43-L49

---

# 8. Authentication and Authorization

## Authentication

- login
- logout
- password change
- password reset
- secure session
- inactive-session expiration
- failed-login lock

## Roles

```text
ADMIN
FACULTY
STUDENT
```

## Authorization model

```text
Request
  ↓
Authentication
  ↓
Role check
  ↓
Academic/resource scope check
  ↓
Business-rule check
  ↓
Database operation
```

Students cannot directly modify attendance.

Faculty can only access attendance and requests within authorized courses/sections.

Administrative functions require admin authorization.

The SRS requires these restrictions at the API/security level, not just through frontend visibility. fileciteturn0file3L315-L341

---

# 9. Smart Attendance Architecture

## No IoT hardware

The dedicated IoT concept is removed.

The faculty member's laptop/desktop camera is the capture device.

```text
Faculty browser
    ↓
Camera permission
    ↓
Live camera
    ↓
Frame capture
    ↓
Vision service
    ↓
Face detection
    ↓
Embedding
    ↓
Similarity / recognition
    ↓
Identity verification
    ↓
Duplicate check
    ↓
Attendance record
```

The SRS requires facial recognition, identity verification, timestamps, duplicate prevention and manual fallback. fileciteturn0file3L354-L365 fileciteturn0file3L389-L426

## Recognition states

The system must expose:

- requesting permission
- permission denied
- camera unavailable
- camera active
- processing
- recognized
- unknown
- multiple faces
- duplicate
- recorded
- recognition error
- manual fallback

## Manual fallback

```text
Recognition unavailable
        ↓
Faculty opens manual attendance
        ↓
Mark/update attendance
        ↓
Reason required where modification occurs
        ↓
Audit log
```

---

# 10. Course and Timetable

Supports:

- departments
- academic years
- semesters
- sections
- courses
- faculty allocation
- classrooms
- timetable
- lecture generation
- cancellation
- rescheduling
- conflict detection

The SRS requires faculty and classroom conflict prevention. fileciteturn0file3L485-L524

---

# 11. Analytics

Core calculations:

```text
attendance % =
attended lectures / conducted lectures × 100
```

### Student analytics
- overall percentage
- course percentage
- history
- projected attendance
- recovery plan

### Faculty analytics
- course/section attendance
- student-level history
- trends
- defaulters

### Admin analytics
- aggregate institutional/academic-scope information

---

# 12. Recovery Planner

For:

```text
P = attended
C = conducted
T = target
```

find the minimum `x` such that:

```text
(P + x) / (C + x) >= T
```

The system returns:

- current attendance
- target
- required future lectures
- projected percentage
- target-achievability status

The SRS explicitly requires this behavior. fileciteturn0file3L608-L621

---

# 13. Predictive Attendance Alerts

Use explainable projection rather than unnecessary ML.

```text
Current state
    +
Potential future absences
    ↓
Projected attendance
    ↓
Threshold comparison
    ↓
Risk?
    ↓
Generate alert
```

This matches the SRS definition of predictive low-attendance alerts. fileciteturn0file3L622-L634

---

# 14. Exception / Regularization

Workflow:

```text
Student request
    ↓
Reason + dates/lectures
    ↓
Supporting document
    ↓
Pending
    ↓
Faculty review
    ├── Approve → attendance regularization
    └── Reject  → decision + reason
    ↓
Audit
    ↓
Notification
```

This aligns with the existing `ApproveLeave` and `ReviewException` sequence diagrams. fileciteturn0file0L10-L13

---

# 15. Notifications

Asynchronous architecture:

```text
Primary transaction
      ↓
Commit
      ↓
Notification job/event
      ↓
Worker
      ├── In-app
      ├── Email
      └── SMS
```

Notification failure must not fail the original attendance/leave operation. fileciteturn0file3L778-L790

---

# 16. Files

Supporting documents are stored in object storage.

Flow:

```text
Upload
 ↓
Validate type/size
 ↓
Store securely
 ↓
Persist metadata
 ↓
Associate with request
```

Access is role-restricted. fileciteturn0file3L719-L736

---

# 17. Audit

Audit important actions:

- login success/failure
- attendance modification
- regularization
- user administration
- academic changes
- configuration changes

Attendance correction records:

- actor
- timestamp
- original state
- new state
- reason

The SRS requires audit history for attendance and security-sensitive actions. fileciteturn0file3L40-L43

---

# 18. Non-Functional Targets

| Requirement | Target |
|---|---:|
| Dashboard | ≤ 3 sec |
| Login | ≤ 3 sec |
| Attendance write after recognition | ≤ 2 sec |
| Analytics update | ≤ 5 sec |
| Attendance history | ≤ 3 sec |
| Defaulter generation | ≤ 10 sec |
| Concurrent authenticated users | ≥ 100 |
| Recovery calculation | ≤ 2 sec |

These are taken directly from the SRS. fileciteturn0file3L965-L983

---

# 19. Testing

## Backend

- unit tests
- service tests
- repository tests
- API integration tests

## Integration

- contract tests
- end-to-end tests
- browser + API flows
- camera workflow tests using controlled test fixtures/mocks

## Critical journeys

```text
Student login
→ dashboard
→ attendance
→ recovery
→ leave request
→ faculty decision
→ updated attendance
→ notification

Faculty login
→ class
→ attendance session
→ recognition/manual fallback
→ analytics

Admin login
→ users
→ academic structure
→ configuration
→ audit
```

The SRS requires independent feature testability and sufficient operational logs. fileciteturn0file3L41-L49

---

# 20. Deployment

Containerized system:

```text
Next.js
   ↓
FastAPI
   ├── PostgreSQL
   ├── Vision processing
   ├── Worker
   └── Object storage
```

The exact infrastructure provider remains replaceable.

---

# 21. Architectural Rules

1. Do not introduce IoT hardware back into the design.
2. Do not build fake AI functionality merely for presentation.
3. Do not place business logic in frontend components.
4. Do not rely on frontend-only authorization.
5. Do not create a monolithic backend.
6. Do not duplicate business calculations across frontend and backend.
7. Do not modify the `frontend/` implementation once Tanuj supplies it except where explicitly required for integration.
8. Keep configuration values configurable.
9. Keep external notification providers behind adapters.
10. Keep the vision module replaceable behind a service boundary.

---

# 22. Final Architecture

```text
attendance-management-system/
│
├── frontend/                 ← Tanuj will supply this
│
├── backend/                  ← Codex owns
│   ├── API
│   ├── Auth/RBAC
│   ├── Database
│   ├── Attendance
│   ├── Vision
│   ├── Analytics
│   ├── Exceptions
│   ├── Notifications
│   ├── Workers
│   └── Tests
│
├── integration/              ← Codex owns after backend baseline
│   ├── Contracts
│   ├── E2E
│   ├── Fixtures
│   └── Scripts
│
├── docs/
├── docker-compose.yml
└── .env.example
```

This structure is the implementation baseline for the rest of the project.

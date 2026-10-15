# CodeForge Backend Architecture

**Version:** 0.3.0 (TA-2 — Phase A1 + A2 complete)

## Overview

The CodeForge backend is a **FastAPI** application backed by **PostgreSQL**, with a **Celery** worker that executes Java/Python code in ephemeral **Docker** containers.

```
Browser ──HTTP──▶ FastAPI (api:8000)
                       │
                       │ .delay()
                       ▼
                  Celery Worker (worker)
                       │
                       │ docker SDK
                       ▼
                  Sandbox Container (ephemeral)
                  codeforge-sandbox-java | codeforge-sandbox-python
```

---

## Implementation Status

| Phase | Description | Status |
|---|---|---|
| Phase 0 | Schema, migrations, config, sandbox image | ✅ Done |
| Phase A1 | Auth system (register, login, refresh, me, JWT deps) | ✅ Done |
| Phase A2 | Course CRUD, problem CRUD, bulk import, gradebook | ✅ Done |
| Phase A3 | Lab sessions + badge engine | 🔲 Planned |
| Phase A4 | Submission history, user profile, security hardening | 🔲 Planned |
| Phase A5 | Polish + single-exe installer + monitoring | 🔲 Planned |

---

## Request Flow

### Auth (JWT)

```
POST /api/v1/auth/login
        │
        ├─ Look up User by email
        ├─ bcrypt verify password
        ├─ Create access token (HS256, 15 min) + refresh token (7 days)
        └─ Return { access_token, refresh_token, user }

Protected endpoints:
        │
        ├─ Extract Bearer token from Authorization header
        ├─ jwt.decode() → payload { sub: user_id, role, type }
        └─ SELECT User WHERE id = payload.sub
```

### Run / Submit

```
POST /api/v1/problems/{slug}/run   (auth required)
        │
        ├─ get_current_user (JWT) → User
        ├─ Fetch problem from DB (ensure it exists)
        ├─ Create Submission record (status: "queued", user_id=current_user.id)
        ├─ grade_submission.delay(submission_id)  ← non-blocking
        └─ Return { submission_id }
                │
                │ (async, in worker process)
                ▼
        grade_submission(submission_id)
                │
                ├─ Update status → "running"
                ├─ Write Solution.java / solution.py to temp dir
                ├─ Compile: javac in sandbox container (Java only)
                │       └─ If fail → status: "compile_error"
                │
                └─ For each test case:
                        ├─ Create ephemeral container
                        ├─ Copy source/class files
                        ├─ Feed stdin
                        ├─ Capture stdout/stderr
                        ├─ Compare normalize(stdout) == normalize(expected)
                        └─ Remove container (try/finally)
                │
                └─ Update Submission with results, score, status

GET /api/v1/submissions/{id}   ← polled by frontend every 1.5s
        └─ Return current Submission state
```

---

## File Structure

```
backend/
├── pytest.ini
├── requirements.txt
├── Dockerfile
├── alembic.ini
├── alembic/
│   ├── env.py                  # Async migration runner
│   └── versions/
│       └── 8f615a4a5063_ta2_schema.py  ← Phase 0 migration (applied)
└── app/
    ├── main.py                 # FastAPI app v0.3.0, CORS, router registration
    ├── config.py               # Pydantic settings (reads .env)
    ├── db.py                   # Async SQLAlchemy engine + Base + get_db
    ├── dependencies.py         # get_current_user, require_instructor, RequireEnrollment
    ├── models/
    │   ├── __init__.py         # Re-exports all models (for Alembic detection)
    │   ├── user.py             # User (id, email, name, role, password_hash)
    │   ├── course.py           # Course (id, title, created_by, invite_code)
    │   ├── enrollment.py       # Enrollment (user_id, course_id, role)
    │   ├── problem.py          # Problem (course_id, created_by, slug, test_cases…)
    │   ├── test_case.py        # TestCase (problem_id, label, input, expected, visible)
    │   ├── submission.py       # Submission (user_id, problem_id, lab_session_id, score…)
    │   ├── lab_session.py      # LabSession + LabSessionProblem (Phase A3)
    │   └── badge.py            # Badge (user_id, lab_session_id, problem_id)
    ├── schemas/
    │   ├── __init__.py
    │   ├── auth.py             # RegisterRequest, LoginRequest, TokenResponse, UserResponse
    │   ├── course.py           # CourseCreate, CourseResponse, CourseDetailResponse, EnrollmentResponse, CourseMemberResponse
    │   ├── problem.py          # ProblemCreate, ProblemUpdate, ProblemDetail, ProblemSummary, BulkImportRequest/Response
    │   ├── lab.py              # LabSessionCreate, LabDashboardResponse (Phase A3)
    │   └── submission.py       # RunRequest, SubmissionCreated, SubmissionResponse
    ├── routers/
    │   ├── __init__.py
    │   ├── auth.py             # POST /auth/register, /login, /refresh; GET /auth/me
    │   ├── courses.py          # Course CRUD, Join, Members, Problem CRUD, Bulk Import, Gradebook
    │   ├── problems.py         # Legacy GET /problems, GET /problems/{slug}, POST /problems/{slug}/run|submit
    │   └── submissions.py      # GET /submissions/{id}
    ├── services/
    │   ├── __init__.py
    │   └── auth_service.py     # hash_password, verify_password, create/decode JWT tokens
    └── worker/
        ├── celery_app.py       # Celery instance + config
        ├── sync_db.py          # Sync SQLAlchemy session for Celery tasks
        ├── tasks.py            # grade_submission Celery task
        └── sandbox.py          # Docker execution engine (Java + Python)

tests/
    ├── test_api.py             # 10 tests: problems + submissions legacy endpoints
    ├── test_auth.py            # 28 tests: auth service + auth endpoints
    ├── test_courses.py         # 34 tests: course CRUD, problem CRUD, gradebook
    └── test_sandbox.py         # 14 tests: Docker sandbox execution
```

---

## Database Schema

```
users
├── id             UUID PK
├── email          VARCHAR(255) UNIQUE
├── name           VARCHAR(255)
├── role           VARCHAR(32)          ← instructor | student
├── password_hash  VARCHAR(256)
└── created_at     TIMESTAMPTZ

courses
├── id             UUID PK
├── title          VARCHAR(256)
├── description    TEXT nullable
├── created_by     UUID FK → users.id (CASCADE)
├── invite_code    VARCHAR(16) UNIQUE   ← 6-char alphanumeric
└── created_at     TIMESTAMPTZ

enrollments
├── id             UUID PK
├── user_id        UUID FK → users.id (CASCADE)
├── course_id      UUID FK → courses.id (CASCADE)
├── role           VARCHAR(32)          ← instructor | student | ta
├── joined_at      TIMESTAMPTZ
└── UNIQUE(user_id, course_id)

problems
├── id             UUID PK
├── course_id      UUID FK → courses.id (CASCADE)
├── created_by     UUID FK → users.id (SET NULL)
├── slug           VARCHAR(128) UNIQUE
├── title          VARCHAR(256)
├── description    TEXT                 ← Markdown
├── difficulty     VARCHAR(16)          ← easy | medium | hard
├── starter_code_java TEXT
├── starter_code_python TEXT nullable
├── time_limit_sec INT (default 10)
├── memory_limit_mb INT (default 128)
└── created_at     TIMESTAMPTZ

test_cases
├── id             UUID PK
├── problem_id     UUID FK → problems.id (CASCADE)
├── label          VARCHAR(16)          ← "01", "02", ...
├── input_data     TEXT
├── expected_output TEXT
├── is_visible     BOOL
└── order_index    INT

submissions
├── id             UUID PK
├── problem_id     UUID FK → problems.id (CASCADE)
├── user_id        UUID FK → users.id (CASCADE)
├── lab_session_id UUID FK → lab_sessions.id (SET NULL) nullable
├── language       VARCHAR(32)          ← java | python
├── source_code    TEXT
├── status         VARCHAR(32)          ← queued|running|completed|compile_error|error|timeout
├── is_full_submit BOOL
├── score          INT nullable          ← 0-100
├── total_cases    INT nullable
├── passed_cases   INT nullable
├── results_json   JSON nullable         ← array of per-test-case results
├── execution_time_ms INT nullable
└── submitted_at   TIMESTAMPTZ

lab_sessions  (Phase A3)
├── id, course_id, title, starts_at, ends_at, mandatory_count, is_active, created_at

lab_session_problems  (Phase A3)
├── id, lab_session_id, problem_id, order_index

badges  (Phase A3)
├── id, user_id, lab_session_id, problem_id, earned_at
└── UNIQUE(user_id, lab_session_id, problem_id)
```

### `results_json` Structure (per submission)
```json
[
  {
    "test_case_id": "uuid",
    "label": "01",
    "is_visible": true,
    "passed": true,
    "expected_output": "Hello World",
    "actual_output": "Hello World",
    "execution_time_ms": 45,
    "error": null
  }
]
```
> Hidden test cases (`is_visible: false`) have `expected_output` and `actual_output` nulled before saving — students only see pass/fail.

---

## API Surface

All endpoints mounted at `/api/v1`. Full request/response schemas: see [`api-contracts.md`](./api-contracts.md).

### Auth ✅
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Register new user |
| `POST` | `/auth/login` | Public | Login, receive JWT tokens |
| `POST` | `/auth/refresh` | Public | Refresh access token |
| `GET` | `/auth/me` | User | Current user profile |

### Courses ✅
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/courses` | Instructor | Create course (auto-generates invite code, auto-enrolls creator) |
| `GET` | `/courses` | User | List enrolled courses |
| `GET` | `/courses/{id}` | Enrolled | Course details |
| `POST` | `/courses/{id}/join` | User | Join via invite code |
| `GET` | `/courses/{id}/members` | Course instructor | Member list |

### Problems ✅
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/courses/{id}/problems` | Course instructor | Create problem + test cases |
| `POST` | `/courses/{id}/problems/bulk-import` | Course instructor | Bulk import from JSON array |
| `GET` | `/courses/{id}/problems` | Enrolled | List course problems |
| `GET` | `/courses/{id}/problems/{pid}` | Enrolled | Problem detail |
| `PUT` | `/problems/{id}` | Course instructor | Update problem / replace test cases |
| `DELETE` | `/problems/{id}` | Course instructor | Delete problem (cascades) |

### Gradebook ✅
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/courses/{id}/gradebook` | Course instructor | Student × Problem score matrix |

### Submissions ✅
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/problems/{slug}/run` | User | Run against visible test cases |
| `POST` | `/problems/{slug}/submit` | User | Submit for full grade |
| `GET` | `/submissions/{id}` | Public* | Poll submission status |

### Lab Sessions & Badges 🔲 (Phase A3)
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/courses/{id}/labs` | Instructor | Create lab session |
| `GET` | `/courses/{id}/labs` | Enrolled | List labs |
| `GET` | `/labs/{id}` | Enrolled | Lab details + problems |
| `GET` | `/labs/{id}/dashboard` | Instructor | Live student progress |
| `GET` | `/labs/{id}/my-progress` | Student | Own progress + badges |

---

## Sandbox Security Model

| Constraint | Value |
|---|---|
| Memory limit | `memory_limit_mb` m per problem (default 128m) |
| CPU limit | 0.5 CPU (cpu_quota=50000, cpu_period=100000) |
| Network | Disabled (`network_disabled=True`) |
| Capabilities | All dropped (`cap_drop=["ALL"]`) |
| Privilege escalation | Blocked (`security_opt=["no-new-privileges"]`) |
| `/tmp` tmpfs | 32MB, noexec, nosuid |
| User | Non-root `runner` (set in sandbox Dockerfile) |
| Timeout | `time_limit_sec` per problem (default 10s) |
| Cleanup | `container.remove(force=True)` in `finally` block |

---

## Submission Status Machine

```
queued → running → completed
                ├→ compile_error
                ├→ timeout
                └→ error
```

---

## Development Commands

```bash
# Start DB + Redis (required for tests)
docker compose up -d db redis

# Rebuild API image (e.g. after requirements.txt change)
docker compose build api worker

# Run all tests
docker compose run -v ./backend:/app --rm api pytest -v

# Apply database migrations
docker compose run --rm api alembic upgrade head

# View API docs (Swagger)
# Start the API: docker compose up api
# Then open: http://localhost:8000/docs

# Worker logs
docker compose logs -f worker

# API logs
docker compose logs -f api
```

# CodeForge Backend Architecture

**Version:** 0.6.0 (Final Jury Milestone — Phase 0 Schema & Foundation Complete)

## Overview

The CodeForge backend is a **FastAPI** application backed by **PostgreSQL**, with a **Celery** worker that executes Java/Python/C/C++ code in ephemeral **Docker** containers.

```
Browser ──HTTP/WS──▶ FastAPI (api:8000)
                           │
                           │ .delay()
                           ▼
                      Celery Worker (worker)
                           │
                           │ docker SDK
                           ▼
                      Sandbox Container (ephemeral)
  codeforge-sandbox-java | codeforge-sandbox-python | codeforge-sandbox-c | codeforge-sandbox-cpp
```

---

## Implementation Status

| Milestone Phase | Description | Status |
|---|---|---|
| TA-1 & TA-2 | Core engine, Auth, Courses, Labs, Badges, Gradebook | ✅ Done |
| Final Jury Phase 0 | Multi-language images (C/C++), DB models, Alembic migration, API contracts | ✅ Done |
| Final Jury A1 | WebSocket real-time submission updates (Redis Pub/Sub) | 📋 Ready |
| Final Jury A2 | C/C++ execution & sandbox security hardening | 📋 Ready |
| Final Jury A3 | Learning modules system (Lessons, Videos, Exercises) | 📋 Ready |
| Final Jury A4 | Proctored assessment & anti-cheat engine | 📋 Ready |
| Final Jury A5 | Analytics dashboard & weighted grading | 📋 Ready |
| Final Jury A6 | Turnkey installer polish & health checks | 📋 Ready |

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
codeforge-setup.sh              # Single-command turnkey deployer & verifier
backend/
├── pytest.ini
├── requirements.txt
├── Dockerfile
├── alembic.ini
├── alembic/
│   ├── env.py                  # Async migration runner
│   └── versions/
│       ├── 8f615a4a5063_ta2_schema.py        ← TA-2 schema
│       └── 20261122_0513_9fdb9d0e7422_final_jury_schema.py ← Final jury schema (applied)
└── app/
    ├── main.py                 # FastAPI app v0.5.0, CORS, router registration
    ├── config.py               # Pydantic settings (reads .env)
    ├── db.py                   # Async SQLAlchemy engine + Base + get_db
    ├── dependencies.py         # get_current_user, require_instructor, RequireEnrollment
    ├── seed.py                 # Database seeder (admin/student users, CS101, problems, lab)
    ├── models/
    │   ├── __init__.py         # Re-exports all models (for Alembic detection)
    │   ├── user.py             # User (id, email, name, role, password_hash)
    │   ├── course.py           # Course (id, title, created_by, invite_code)
    │   ├── enrollment.py       # Enrollment (user_id, course_id, role)
    │   ├── problem.py          # Problem (course_id, slug, starter_code_c, starter_code_cpp…)
    │   ├── test_case.py        # TestCase (problem_id, label, input, expected, weight…)
    │   ├── submission.py       # Submission (user_id, exam_session_id, custom_input…)
    │   ├── lab_session.py      # LabSession + LabSessionProblem
    │   ├── badge.py            # Badge (user_id, lab_session_id, problem_id)
    │   ├── learning_module.py  # LearningModule (course_id, title, is_published…)
    │   ├── learning_content.py # LearningContent (module_id, content_type, body…)
    │   ├── module_progress.py  # ModuleProgress (user_id, module_id, is_completed…)
    │   ├── exam.py             # Exam + ExamProblem (duration, anti-cheat flags…)
    │   ├── exam_session.py     # ExamSession (user_id, exam_id, total_score…)
    │   └── exam_violation.py   # ExamViolation (violation_type, details…)
    ├── schemas/
    │   ├── __init__.py
    │   ├── auth.py             # RegisterRequest, LoginRequest, TokenResponse, UserResponse
    │   ├── course.py           # CourseCreate, CourseResponse, CourseDetailResponse, EnrollmentResponse, CourseMemberResponse
    │   ├── problem.py          # ProblemCreate, ProblemUpdate, ProblemDetail, ProblemSummary, BulkImportRequest/Response
    │   ├── lab.py              # LabSessionCreate, LabSessionUpdate, LabSessionResponse, LabSessionDetailResponse, LabDashboardResponse, StudentLabProgressResponse
    │   └── submission.py       # RunRequest, SubmitRequest, SubmissionCreated, SubmissionResponse, SubmissionSummaryResponse
    ├── routers/
    │   ├── __init__.py
    │   ├── auth.py             # POST /auth/register, /login, /refresh; GET /auth/me
    │   ├── courses.py          # Course CRUD, Join, Members, Problem CRUD, Bulk Import, Gradebook
    │   ├── problems.py         # GET /problems, GET /problems/{slug}, POST /problems/{slug}/run|submit, GET /problems/{id}/submissions
    │   ├── submissions.py      # GET /submissions/{id} (auth-gated)
    │   └── labs.py             # Lab CRUD, Dashboard, Student Progress
    ├── services/
    │   ├── __init__.py
    │   ├── auth_service.py     # hash_password, verify_password, create/decode JWT tokens
    │   └── badge_service.py    # evaluate_badges_sync, evaluate_badges_async
    └── worker/
        ├── celery_app.py       # Celery instance + config
        ├── sync_db.py          # Sync SQLAlchemy session for Celery tasks
        ├── tasks.py            # grade_submission Celery task
        └── sandbox.py          # Docker execution engine (Java + Python)

tests/
    ├── test_api.py             # 10 tests: problems + submissions legacy endpoints
    ├── test_auth.py            # 28 tests: auth service + auth endpoints
    ├── test_courses.py         # 34 tests: course CRUD, problem CRUD, gradebook
    ├── test_labs.py            # 10 tests: lab CRUD, dashboard, badge engine, student progress
    ├── test_sandbox.py         # 20 tests: Java + Python Docker sandbox execution
    └── test_submissions_history.py # 8 tests: submission history & access control
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
| `GET` | `/submissions/{id}` | User (Owner/Instructor) | Poll submission status |
| `GET` | `/problems/{id_or_slug}/submissions` | User | Past submissions for problem with `is_best` |

### Lab Sessions & Badges ✅
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/courses/{id}/labs` | Instructor | Create lab session + attach problems |
| `GET` | `/courses/{id}/labs` | Enrolled | List course labs with problem counts |
| `GET` | `/labs/{id}` | Enrolled | Lab details + ordered problem list |
| `PUT` | `/labs/{id}` | Instructor | Update lab details / reassign problems |
| `GET` | `/labs/{id}/dashboard` | Instructor | Live student progress & badge leaderboard |
| `GET` | `/labs/{id}/my-progress` | Enrolled | Current student solves, badges, recent badge |

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

## Development & Deployment Commands

```bash
# Turnkey deployment (verifies prerequisites, builds sandboxes, runs migrations, seeds DB)
./codeforge-setup.sh

# Turnkey deployment with rebuild of core API/worker images
./codeforge-setup.sh --build

# Run all tests (106 tests across auth, courses, labs, sandbox, submissions)
docker compose run -v ./backend:/app --rm api pytest -v

# Run database migrations manually
docker compose run --rm api alembic upgrade head

# Re-run database seeding manually
docker compose exec api python -m app.seed

# View API documentation (Swagger)
# Open: http://localhost:8000/docs

# Tail logs
docker compose logs -f api
docker compose logs -f worker
```

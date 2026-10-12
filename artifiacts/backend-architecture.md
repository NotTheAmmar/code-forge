# CodeForge Backend Architecture

## Overview

The CodeForge backend is a **FastAPI** application backed by **PostgreSQL**, with a **Celery** worker that executes Java code in ephemeral **Docker** containers.

```
Browser ──HTTP──▶ Nginx ──proxy──▶ FastAPI (api:8000)
                                        │
                                        │ .delay()
                                        ▼
                                   Celery Worker (worker)
                                        │
                                        │ docker SDK
                                        ▼
                                   Sandbox Container (ephemeral)
                                   codeforge-sandbox-java
```

---

## Request Flow

### Run / Submit

```
POST /api/v1/problems/{slug}/run
        │
        ├─ Fetch problem from DB (ensure it exists)
        ├─ Create Submission record (status: "queued")
        ├─ grade_submission.delay(submission_id)  ← non-blocking
        └─ Return { submission_id }
                │
                │ (async, in worker process)
                ▼
        grade_submission(submission_id)
                │
                ├─ Update status → "running"
                ├─ Write Solution.java to temp dir
                ├─ Compile: javac in sandbox container
                │       └─ If fail → status: "compile_error"
                │
                └─ For each test case:
                        ├─ Create ephemeral container
                        ├─ Copy .class files
                        ├─ Feed stdin
                        ├─ Capture stdout/stderr
                        ├─ Compare normalize(stdout) == normalize(expected)
                        └─ Remove container (try/finally)
                │
                └─ Update Submission with results

GET /api/v1/submissions/{id}   ← polled by frontend every 1.5s
        └─ Return current Submission state
```

---

## File Structure

```
backend/
├── manage.py                   # CLI: python manage.py load-problems ./problems/
├── pytest.ini
├── requirements.txt
├── Dockerfile
├── alembic.ini
├── alembic/
│   ├── env.py                  # Async migration runner
│   ├── script.py.mako
│   └── versions/               # Generated migration files
└── app/
    ├── main.py                 # FastAPI app, CORS, router registration
    ├── config.py               # Pydantic settings (reads .env)
    ├── db.py                   # Async SQLAlchemy engine + get_db dependency
    ├── dependencies.py         # Re-exports get_db
    ├── models/
    │   ├── __init__.py         # Re-exports all models
    │   ├── user.py             # User account ORM model
    │   ├── course.py           # Course ORM model
    │   ├── enrollment.py       # Course membership ORM model
    │   ├── lab_session.py      # LabSession & LabSessionProblem ORM models
    │   ├── badge.py            # 1-to-1 Problem Badge ORM model
    │   ├── problem.py          # Problem ORM model
    │   ├── test_case.py        # TestCase ORM model
    │   └── submission.py       # Submission ORM model
    ├── schemas/
    │   ├── __init__.py
    │   ├── auth.py             # RegisterRequest, LoginRequest, UserResponse, TokenResponse
    │   ├── course.py           # CourseCreate, CourseResponse, CourseDetailResponse
    │   ├── lab.py              # LabSessionCreate, LabDashboardResponse, StudentLabProgressResponse
    │   ├── problem.py          # ProblemCreate, ProblemUpdate, BulkImportRequest, ProblemDetail
    │   └── submission.py       # RunRequest, SubmitRequest, SubmissionResponse, GradebookResponse
    ├── routers/
    │   ├── __init__.py
    │   ├── auth.py             # Register, Login, Refresh, Me
    │   ├── courses.py          # Course CRUD, Join, Members, Gradebook
    │   ├── labs.py             # Lab CRUD, Dashboard, Student Progress
    │   ├── problems.py         # Course-scoped Problem CRUD & Bulk Import
    │   └── submissions.py      # Run, Submit, Poll Submission, History
    ├── worker/
    │   ├── celery_app.py       # Celery instance + config
    │   ├── sync_db.py          # Sync SQLAlchemy session for Celery tasks
    │   ├── tasks.py            # grade_submission Celery task
    │   └── sandbox.py          # Docker execution engine
    └── websocket/
        └── submissions_ws.py   # (Future: real-time WebSocket updates)
```

---

## Database Schema

```
problems
├── id             UUID PK
├── slug           VARCHAR(128) UNIQUE  ← matches problems/ folder name
├── title          VARCHAR(256)
├── description    TEXT                 ← Markdown from description.md
├── difficulty     VARCHAR(16)          ← easy | medium | hard
├── starter_code_java TEXT
├── time_limit_sec INT (default 10)
├── memory_limit_mb INT (default 128)
└── created_at     TIMESTAMPTZ

test_cases
├── id             UUID PK
├── problem_id     UUID FK → problems.id (CASCADE DELETE)
├── label          VARCHAR(16)   ← "01", "02", ...
├── input_data     TEXT          ← contents of XX.in
├── expected_output TEXT         ← contents of XX.out
├── is_visible     BOOL
└── order_index    INT

submissions
├── id             UUID PK
├── problem_id     UUID FK → problems.id (CASCADE DELETE)
├── language       VARCHAR(32) (default "java")
├── source_code    TEXT
├── status         VARCHAR(32)   ← queued|running|completed|compile_error|error|timeout
├── is_full_submit BOOL          ← False=Run (visible only), True=Submit (all)
├── score          INT nullable  ← 0-100 percentage
├── total_cases    INT nullable
├── passed_cases   INT nullable
├── results_json   JSON nullable ← array of TestCaseResult objects
├── execution_time_ms INT nullable
└── submitted_at   TIMESTAMPTZ
```

### results_json Schema

```json
[
  {
    "test_case_id": "uuid",
    "label": "01",
    "is_visible": true,
    "passed": true,
    "expected_output": "Hello, Alice!",
    "actual_output": "Hello, Alice!",
    "execution_time_ms": 42,
    "error": null
  }
]
```

> **Privacy rule:** For hidden test cases (is_visible: false), expected_output and actual_output are set to null before saving. Frontend only receives pass/fail for hidden cases.

---

## API Contract

All endpoints are mounted under /api/v1 (proxied by Nginx from /api/v1).

| Method | Endpoint | Description | Returns |
|---|---|---|---|
| GET | /problems | List all problems | ProblemSummary[] |
| GET | /problems/{slug} | Full problem + test cases | ProblemDetail |
| POST | /problems/{slug}/run | Run against visible tests | { submission_id } 202 |
| POST | /problems/{slug}/submit | Run against all tests | { submission_id } 202 |
| GET | /submissions/{id} | Polling endpoint for status | SubmissionResponse |
| GET | /health | Liveness probe | { status: "ok" } |
| GET | /metrics | Prometheus metrics scrape | text/plain (Prometheus format) |

---

## Sandbox Security Model

| Constraint | Value |
|---|---|
| Memory limit | memory_limit_mb m (per problem, default 128m) |
| CPU limit | 0.5 CPU (cpu_quota=50000, cpu_period=100000) |
| Network | Disabled (network_disabled=True) |
| Root filesystem | Writable (required for `put_archive`; write access is harmless as network is disabled and user is non-root) |
| /tmp tmpfs | 32MB, noexec,nosuid |
| Capabilities | All dropped (cap_drop=["ALL"]) |
| Privilege escalation | Blocked (security_opt=["no-new-privileges"]) |
| User | Non-root runner (set in sandbox Dockerfile) |
| Timeout | time_limit_sec seconds (per problem, default 10s) |
| Cleanup | container.remove(force=True) in finally block |

---

## Submission Status Machine

```
queued --> running --> completed
                  |--> compile_error
                  |--> timeout
                  `--> error
```

- **queued** - Submission created, waiting for Celery worker
- **running** - Worker started execution
- **completed** - All test cases evaluated (some may have failed, check score)
- **compile_error** - javac failed. results_json[0].error contains javac output
- **timeout** - At least one test case exceeded time_limit_sec
- **error** - Unexpected system error (Docker daemon issue, etc.)

---

## Problem Loader CLI

```bash
# Load all problems
docker compose exec api python manage.py load-problems ./problems/

# Load a single problem
docker compose exec api python manage.py load-problems ./problems/two-sum/

# Idempotent - safe to re-run after edits
```

---

## Development Commands

```bash
# Build and start the full stack
docker compose up -d --build

# Run database migrations
docker compose exec api alembic upgrade head

# Load sample problems
docker compose exec api python manage.py load-problems ./problems/

# View API docs
open http://localhost:8000/docs

# Run fast tests (no Docker)
docker compose exec api pytest tests/test_api.py -v

# Run sandbox tests (requires Docker socket)
docker compose exec api pytest tests/test_sandbox.py -v -s -m sandbox

# Worker logs
docker compose logs -f worker

# API logs
docker compose logs -f api
```

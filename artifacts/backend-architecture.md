# CodeForge Backend Architecture

**Version:** 1.0.0 (Final Jury Complete)  
**Status:** ✅ All 7 Phases (0, A1–A6) Implemented, Tested, & Verified (145/145 Tests Passing)

---

## 🌟 Overview

CodeForge is a modern, enterprise-ready automated programming judge, learning management, and proctored assessment platform. The backend is powered by **FastAPI** (Python 3.12) and **PostgreSQL 16**, asynchronous task grading via **Celery** on **Redis 7**, real-time test streaming via **WebSockets + Redis Pub/Sub**, and fully isolated ephemeral **Docker** sandboxes for **Python**, **Java**, **C**, and **C++**.

```
                           Browser Client (React 18 / Vite / Monaco)
                                        │               ▲
                            HTTP REST   │               │ WebSocket
                         /api/v1/*      │               │ /ws/submissions/{id}
                                        ▼               │
                         ┌──────────────────────────────────────┐
                         │      FastAPI Application (api:8000)   │
                         └──────────────────┬───────────────────┘
                                            │
                      Enqueues task         │ Publishes status updates
                      (grade_submission)    │ (test progression)
                                            ▼
                         ┌──────────────────────────────────────┐
                         │           Redis 7 (redis:6379)       │
                         │     - Celery Task Queue Broker       │
                         │     - Real-Time Pub/Sub Channel      │
                         │     - Rate Limiter (Token Bucket)    │
                         └──────────────────┬───────────────────┘
                                            │
                                            │ Worker consumes task
                                            ▼
                         ┌──────────────────────────────────────┐
                         │     Celery Worker Process (worker)   │
                         │     - docker-py Container Manager    │
                         │     - Partial Credit Scoring Engine  │
                         │     - Custom Input Runner            │
                         └──────────────────┬───────────────────┘
                                            │
                           docker.run(...)  │ Ephemeral lifecycle
                                            ▼
       ┌─────────────────────────────────────────────────────────────────┐
       │                   Isolated Docker Sandboxes                      │
       │  codeforge-sandbox-python │ codeforge-sandbox-java             │
       │  codeforge-sandbox-c      │ codeforge-sandbox-cpp              │
       │                                                                 │
       │  Security Constraints:                                          │
       │  • network_disabled=True (Zero external network access)         │
       │  • pids_limit=64 (Prevents fork bombs)                          │
       │  • mem_limit=128m (Memory bomb containment)                     │
       │  • cpu_quota=50000, cpu_period=100000 (0.5 CPU cap)             │
       │  • ulimit nofile=64:64 (File descriptor exhaustion defense)     │
       │  • tmpfs /tmp: size=16m, noexec, nosuid                         │
       │  • cap_drop=["ALL"], security_opt=["no-new-privileges"]         │
       │  • User: non-root 'runner'                                      │
       └─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Final Jury Implementation Matrix

| Phase | Module | Scope & Architecture | Status |
|---|---|---|---|
| **Phase 0** | **Pre-work & Foundation** | C/C++ Dockerfiles (`sandbox/c`, `sandbox/cpp`), unified Alembic migration `9fdb9d0e7422`, Pydantic models & API contract synchronisation. | ✅ Complete |
| **Phase A1** | **WebSocket Real-Time Streaming** | Redis Pub/Sub WebSocket router (`/ws/submissions/{id}`) with backward-compatible REST polling fallback. | ✅ Complete |
| **Phase A2** | **C/C++ Execution & Hardening** | GCC 13 (`-O2 -Wall -std=c11`) and G++ 20 (`-O2 -Wall -std=c++20`) pipeline, `--pids-limit=64`, `--ulimit nofile=64:64`, tmpfs size & noexec enforcement, adversarial security test suite. | ✅ Complete |
| **Phase A3** | **Learning Modules System** | Structured curricula (`LearningModule`, `LearningContent`, `ModuleProgress`), sequential module unlocking, embedded YouTube videos, Markdown theory, inline practice problems. | ✅ Complete |
| **Phase A4** | **Proctored Assessment System** | Timed exam engine, full-screen lockdown, anti-cheat violation tracking (`tab_switch`, `fullscreen_exit`, `copy_paste`), auto-submission, and instructor audit dashboard. | ✅ Complete |
| **Phase A5** | **Analytics, Custom Input & Scoring** | Course overview analytics, error distribution, student progress tracking, problem performance metrics, partial credit scoring (`test_cases.weight`), and sandboxed arbitrary stdin execution (`/problems/{slug}/run-custom`). | ✅ Complete |
| **Phase A6** | **Installer & Production Polish** | OS auto-detection installer (`codeforge-setup.sh`), Windows PowerShell installer (`codeforge-setup.ps1`), launcher (`codeforge-setup.bat`), health & readiness probes (`/health`, `/health/ready`), and backup runbook. | ✅ Complete |

---

## 🔄 Core Request Flows

### 1. Real-Time Submission & WebSocket Streaming
```
Client                          API Router                     Redis Pub/Sub                 Celery Worker
  │                                  │                               │                             │
  │── POST /problems/{slug}/submit ─▶│                               │                             │
  │                                  │── Creates Submission (queued)─┼────────────────────────────▶│
  │◀─ Returns { submission_id } ─────│                               │                             │
  │                                  │                               │                             │
  │── WS /ws/submissions/{id} ──────▶│                               │                             │
  │                                  │── Subscribes to channel ─────▶│                             │
  │                                  │   "submission:{id}"           │                             │
  │                                  │                               │                             │
  │                                  │                               │◀─ Publishes {"status":      │
  │                                  │                               │      "compiling"} ──────────│
  │◀─ WS message: Compiling ─────────│◀──────────────────────────────│                             │
  │                                  │                               │◀─ Publishes {"status":      │
  │                                  │                               │      "running", 1/5} ───────│
  │◀─ WS message: Running 1/5 ───────│◀──────────────────────────────│                             │
  │                                  │                               │                             │
  │                                  │                               │◀─ Publishes terminal state  │
  │                                  │                               │   {"status": "completed"}──│
  │◀─ WS message: Completed + Scores ─│◀─────────────────────────────│                             │
```

### 2. Custom Input Execution Flow (`POST /problems/{slug}/run-custom`)
1. User provides `source_code`, `language`, and raw `custom_input` (stdin).
2. Endpoint checks Redis rate-limit (10 custom runs per user per minute).
3. Executes synchronously/semi-synchronously via `execute_custom_code` inside the isolated sandbox container without modifying database problem test cases.
4. Returns `stdout`, `stderr`, `execution_time_ms`, and `status` (`completed`, `compile_error`, `timeout`, `error`).

### 3. Proctored Exam Flow with Lockdown
1. Instructor creates `Exam` with `duration_minutes`, `start_time`, `end_time`, problem weightings, and lockdown flags.
2. Student starts `ExamSession` (`POST /exams/{id}/start`). Single active session enforced.
3. Client browser enters full-screen mode and enables event listeners.
4. Any violation (tab switch, window blur, exit full-screen, clipboard paste) fires `POST /exam-sessions/{id}/violations`, recording event type and timestamp.
5. Server enforces server-side expiration: submissions after `ends_at + 60s` are rejected.
6. Upon completion (`POST /exam-sessions/{id}/finish`) or timer expiry, total exam score is computed as the weighted sum of best problem submissions.

---

## 🗄️ Database Architecture (SQLAlchemy 2.0 & PostgreSQL 16)

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
├── invite_code    VARCHAR(16) UNIQUE
└── created_at     TIMESTAMPTZ

enrollments
├── id             UUID PK
├── user_id        UUID FK → users.id (CASCADE)
├── course_id      UUID FK → courses.id (CASCADE)
├── role           VARCHAR(32)          ← instructor | student | ta
└── joined_at      TIMESTAMPTZ

problems
├── id             UUID PK
├── course_id      UUID FK → courses.id (CASCADE)
├── created_by     UUID FK → users.id (SET NULL)
├── slug           VARCHAR(128) UNIQUE
├── title          VARCHAR(256)
├── description    TEXT
├── difficulty     VARCHAR(16)          ← easy | medium | hard
├── starter_code_python TEXT nullable
├── starter_code_java   TEXT nullable
├── starter_code_c      TEXT nullable
├── starter_code_cpp    TEXT nullable
├── time_limit_sec INT (default 10)
├── memory_limit_mb INT (default 128)
└── created_at     TIMESTAMPTZ

test_cases
├── id             UUID PK
├── problem_id     UUID FK → problems.id (CASCADE)
├── label          VARCHAR(16)
├── input_data     TEXT
├── expected_output TEXT
├── is_visible     BOOL
├── weight         FLOAT (default 1.0)  ← Partial credit weighting
└── order_index    INT

submissions
├── id             UUID PK
├── problem_id     UUID FK → problems.id (CASCADE)
├── user_id        UUID FK → users.id (CASCADE)
├── lab_session_id UUID FK → lab_sessions.id (SET NULL) nullable
├── exam_session_id UUID FK → exam_sessions.id (SET NULL) nullable
├── language       VARCHAR(32)          ← python | java | c | cpp
├── source_code    TEXT
├── status         VARCHAR(32)          ← queued | running | completed | compile_error | timeout | error
├── is_full_submit BOOL
├── score          INT nullable          ← 0 to 100 (weighted)
├── total_cases    INT nullable
├── passed_cases   INT nullable
├── results_json   JSON nullable         ← Detailed test case executions
├── execution_time_ms INT nullable
└── submitted_at   TIMESTAMPTZ

learning_modules
├── id             UUID PK
├── course_id      UUID FK → courses.id (CASCADE)
├── title          VARCHAR(256)
├── description    TEXT nullable
├── order_index    INT
├── is_published   BOOL (default False)
├── created_by     UUID FK → users.id (CASCADE)
└── created_at     TIMESTAMPTZ

learning_contents
├── id             UUID PK
├── module_id      UUID FK → learning_modules.id (CASCADE)
├── content_type   VARCHAR(32)          ← text | video | problem
├── title          VARCHAR(256)
├── body           TEXT nullable        ← Markdown theory or YouTube embed URL
├── problem_id     UUID FK → problems.id (SET NULL) nullable
└── order_index    INT

module_progress
├── id             UUID PK
├── user_id        UUID FK → users.id (CASCADE)
├── module_id      UUID FK → learning_modules.id (CASCADE)
├── is_completed   BOOL (default False)
└── completed_at   TIMESTAMPTZ nullable

exams
├── id             UUID PK
├── course_id      UUID FK → courses.id (CASCADE)
├── title          VARCHAR(256)
├── description    TEXT nullable
├── duration_minutes INT
├── start_time     TIMESTAMPTZ
├── end_time       TIMESTAMPTZ
├── is_published   BOOL (default False)
├── require_fullscreen BOOL (default True)
├── block_copy_paste   BOOL (default True)
├── track_tab_switches BOOL (default True)
├── created_by     UUID FK → users.id (CASCADE)
└── created_at     TIMESTAMPTZ

exam_problems
├── id             UUID PK
├── exam_id        UUID FK → exams.id (CASCADE)
├── problem_id     UUID FK → problems.id (CASCADE)
├── points         INT (default 100)
└── order_index    INT

exam_sessions
├── id             UUID PK
├── exam_id        UUID FK → exams.id (CASCADE)
├── user_id        UUID FK → users.id (CASCADE)
├── started_at     TIMESTAMPTZ
├── ends_at        TIMESTAMPTZ
├── submitted_at   TIMESTAMPTZ nullable
├── total_score    INT (default 0)
└── is_active      BOOL (default True)

exam_violations
├── id             UUID PK
├── session_id     UUID FK → exam_sessions.id (CASCADE)
├── violation_type VARCHAR(64)          ← tab_switch | fullscreen_exit | copy_paste
├── timestamp      TIMESTAMPTZ
└── details        TEXT nullable
```

---

## 🔌 API Endpoints Summary

All routes are prefixed by `/api/v1` (with WebSockets available at both `/ws/submissions/{id}` and `/api/v1/ws/submissions/{id}`).

| Category | Endpoint | Methods | Access | Notes |
|---|---|---|---|---|
| **Health** | `/health`, `/health/ready` | `GET` | Public | Liveness probe & readiness probe (DB + Redis checks) |
| **Auth** | `/auth/register`, `/auth/login`, `/auth/refresh` | `POST` | Public | JWT auth (15 min access, 7 day refresh) |
| **Auth** | `/auth/me` | `GET` | User | Logged-in profile |
| **Courses** | `/courses` | `GET`, `POST` | User/Inst. | List or create courses |
| **Courses** | `/courses/{id}`, `/courses/{id}/join`, `/courses/{id}/members` | `GET`, `POST` | Enrolled | Course details, invite join, member roster |
| **Courses** | `/courses/{id}/gradebook` | `GET` | Instructor | Student × Problem score matrix |
| **Problems** | `/courses/{id}/problems`, `/courses/{id}/problems/bulk-import` | `GET`, `POST` | Enrolled/Inst. | Course problem list & JSON bulk import |
| **Problems** | `/problems/{id_or_slug}` | `GET`, `PUT`, `DELETE` | Enrolled/Inst. | Problem details & management |
| **Execution** | `/problems/{slug}/run`, `/problems/{slug}/submit` | `POST` | Enrolled | Asynchronous sandbox execution |
| **Execution** | `/problems/{slug}/run-custom` | `POST` | Enrolled | Sandboxed arbitrary stdin runner (rate-limited) |
| **Submissions** | `/submissions/{id}` | `GET` | Owner/Inst. | Polling fallback for submission status |
| **Submissions** | `/problems/{slug}/submissions` | `GET` | Enrolled | Submission history with `is_best` flags |
| **WebSocket** | `/ws/submissions/{id}` | `WebSocket` | Public/User | Live real-time test progress & result streaming |
| **Learning** | `/courses/{id}/modules`, `/modules/{id}` | `GET`, `POST`, `PUT`, `DELETE` | Enrolled/Inst. | Module curriculum & CRUD |
| **Learning** | `/modules/{id}/contents`, `/contents/{id}` | `POST`, `PUT`, `DELETE` | Instructor | Theory, video embed, challenge management |
| **Learning** | `/modules/{id}/complete`, `/courses/{id}/module-progress` | `POST`, `GET` | Enrolled | Student curriculum progression tracking |
| **Exams** | `/courses/{id}/exams`, `/exams/{id}` | `GET`, `POST`, `PUT`, `DELETE` | Enrolled/Inst. | Exam scheduling & CRUD |
| **Exams** | `/exams/{id}/start`, `/exam-sessions/{id}/finish` | `POST` | Student | Timed session lifecycle management |
| **Exams** | `/exam-sessions/{id}/violations` | `POST` | Student | Anti-cheat violation telemetry logging |
| **Exams** | `/exams/{id}/results`, `/exam-sessions/{id}/my-result` | `GET` | Inst./Student | Exam scoring & violation audit log |
| **Analytics** | `/courses/{id}/analytics` | `GET` | Instructor | Course overview, error distribution, completion |
| **Analytics** | `/courses/{id}/analytics/student/{user_id}` | `GET` | Self/Inst. | Student performance timeline & score progression |
| **Analytics** | `/problems/{id}/analytics` | `GET` | Instructor | Problem pass rate, attempt metrics, error breakdown |

---

## 🔒 Ephemeral Sandbox Isolation

Every piece of user-submitted code runs inside a dedicated, throwaway container.

| Security Layer | Enforced Policy | Prevented Attack Vector |
|---|---|---|
| **Process Limits** | `--pids-limit=64` | `fork()` bombs, exponential process trees |
| **Descriptor Limits** | `--ulimit nofile=64:64` | File descriptor exhaustion (`pipe()`, `open()`) |
| **Memory Ceiling** | `--memory=128m` | Heap/stack memory bombs, OOM containment |
| **CPU Quota** | `--cpu-quota=50000 --cpu-period=100000` | Infinite loops, CPU starvation |
| **Network Isolation** | `network_disabled=True` | Botnet connections, SSRF, data exfiltration |
| **Filesystem Isolation**| Read-only rootfs + tmpfs `/tmp:16m,noexec,nosuid` | Malicious binary drops, binary execution in `/tmp` |
| **Privilege Boundaries**| `cap_drop=["ALL"]`, `no-new-privileges` | Linux capability exploits, setuid privilege escalation |
| **Non-Root Execution** | User: `runner` (`uid=1001`) | Root filesystem tampering |
| **Resource Cleanup** | Container removal in `finally:` block | Zombie containers, resource leakage |

---

## 🚀 Operations & Cross-Platform Installers

CodeForge features zero-dependency single-command setup scripts across all operating systems:
- **Linux & macOS & WSL2:** `./codeforge-setup.sh` (or `./codeforge-setup.sh --build`)
- **Windows PowerShell:** `powershell -ExecutionPolicy Bypass -File .\codeforge-setup.ps1`
- **Windows Double-Click Launcher:** `codeforge-setup.bat`

The installer automatically detects Docker, checks Docker Desktop status, creates `.env` configuration, pulls base images, builds the 4 multi-language sandbox containers (`codeforge-sandbox-python`, `codeforge-sandbox-java`, `codeforge-sandbox-c`, `codeforge-sandbox-cpp`), runs Alembic migrations, and seeds the database.

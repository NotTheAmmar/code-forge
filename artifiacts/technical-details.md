# DockGrade — Technical Details

This document covers the full technical architecture, stack choices, database design, API surface, Docker configuration, and project structure for the semester-scoped implementation of DockGrade.

---

## 📦 Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | React 18+ (Vite) | Fast build tooling, massive ecosystem, seamless Monaco Editor integration. |
| **Code Editor** | Monaco Editor (`@monaco-editor/react`) | The same engine that powers VS Code. Syntax highlighting, autocomplete, and language support for Java/Python out of the box. |
| **UI Styling** | TailwindCSS + shadcn/ui | Utility-first CSS with pre-built, accessible component primitives. Fast to prototype, consistent design. |
| **Backend API** | Python 3.12+ (FastAPI) | Async-native, auto-generated Swagger docs, excellent Docker SDK support, type-safe with Pydantic. |
| **Job Queue** | Redis + Celery | Industry-standard async task queue for Python. Redis acts as both the message broker and result backend. |
| **Database** | PostgreSQL 16 | Rock-solid relational DB. Handles the structured data model (users, courses, problems, submissions, grades). |
| **ORM** | SQLAlchemy 2.0 + Alembic | Async-compatible ORM with migration support. Alembic handles schema versioning. |
| **Docker SDK** | `docker-py` (Python Docker SDK) | Programmatic container lifecycle management — create, start, wait, capture logs, remove. |
| **Real-time** | WebSocket (FastAPI native) | Push submission results to the browser the instant grading completes, no polling. |
| **Monitoring** | Prometheus + Grafana + cAdvisor | Container-level metrics (CPU, memory, network) with live dashboards. Great for jury demo. |
| **Reverse Proxy** | Nginx | Routes frontend static assets and proxies `/api/*` requests to FastAPI. Handles CORS and WebSocket upgrades. |

---

## 🗄️ Database Schema

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
│    users      │       │     courses       │       │   enrollments    │
├──────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)      │──┐    │ id (PK)          │──┐    │ id (PK)          │
│ email        │  │    │ title            │  │    │ user_id (FK)     │
│ name         │  │    │ description      │  │    │ course_id (FK)   │
│ role (enum)  │  │    │ created_by (FK)  │──┘    │ role (enum)      │
│ password_hash│  │    │ invite_code      │       │ joined_at        │
│ created_at   │  │    │ created_at       │       └──────────────────┘
└──────────────┘  │    └──────────────────┘
                  │
                  │    ┌──────────────────┐       ┌──────────────────────┐
                  │    │    problems       │       │     test_cases        │
                  │    ├──────────────────┤       ├──────────────────────┤
                  │    │ id (PK)          │──┐    │ id (PK)              │
                  │    │ course_id (FK)   │  │    │ problem_id (FK)      │
                  │    │ title            │  │    │ input_data (TEXT)     │
                  │    │ description (TEXT)│  ├───│ expected_output (TEXT)│
                  │    │ starter_code_java│  │    │ is_visible (BOOL)    │
                  │    │ starter_code_py  │  │    │ order_index (INT)    │
                  │    │ difficulty (enum)│  │    └──────────────────────┘
                  │    │ time_limit_sec   │  │
                  │    │ memory_limit_mb  │  │
                  │    │ created_at       │  │
                  │    └──────────────────┘  │
                  │                          │
                  │    ┌─────────────────────┴────┐
                  │    │      submissions          │
                  │    ├──────────────────────────┤
                  └───→│ id (PK)                  │
                       │ user_id (FK)             │
                       │ problem_id (FK)          │
                       │ language (enum: java|py) │
                       │ source_code (TEXT)        │
                       │ status (enum)             │
                       │ score (INT)               │
                       │ total_cases (INT)         │
                       │ passed_cases (INT)        │
                       │ results_json (JSONB)      │
                       │ execution_time_ms (INT)   │
                       │ submitted_at              │
                       └──────────────────────────┘
```

### Enums

| Enum | Values |
|---|---|
| `user_role` | `instructor`, `student` |
| `enrollment_role` | `instructor`, `student`, `ta` |
| `difficulty` | `easy`, `medium`, `hard` |
| `language` | `java`, `python` |
| `submission_status` | `queued`, `running`, `completed`, `error`, `timeout` |

### `results_json` Structure (per submission)
Stores individual test case results as a JSONB column for flexible querying:
```json
[
  {
    "test_case_id": 1,
    "is_visible": true,
    "passed": true,
    "expected_output": "Hello World",
    "actual_output": "Hello World",
    "execution_time_ms": 45,
    "error": null
  },
  {
    "test_case_id": 2,
    "is_visible": false,
    "passed": false,
    "expected_output": "42",
    "actual_output": "41",
    "execution_time_ms": 38,
    "error": null
  }
]
```

---

## 🔌 API Design

All endpoints are prefixed with `/api/v1`. Authentication is via JWT tokens in the `Authorization: Bearer <token>` header.

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new user (email, name, password, role). |
| `POST` | `/auth/login` | Returns a JWT access token + refresh token. |
| `POST` | `/auth/refresh` | Refresh an expired access token. |
| `GET` | `/auth/me` | Get the current authenticated user's profile. |

### Courses
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/courses` | Create a new course. | Instructor |
| `GET` | `/courses` | List courses the user is enrolled in. | Any |
| `GET` | `/courses/{id}` | Get course details. | Enrolled |
| `POST` | `/courses/{id}/join` | Join a course via invite code. | Student |
| `GET` | `/courses/{id}/members` | List enrolled students + instructors. | Instructor |

### Problems
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/courses/{id}/problems` | Create a new problem with test cases. | Instructor |
| `GET` | `/courses/{id}/problems` | List all problems in a course. | Enrolled |
| `GET` | `/problems/{id}` | Get problem details (description, starter code, visible test cases). | Enrolled |
| `PUT` | `/problems/{id}` | Update a problem. | Instructor |
| `DELETE` | `/problems/{id}` | Delete a problem and its test cases. | Instructor |

### Submissions
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/problems/{id}/run` | Run code against **visible** test cases only (no grade saved). | Student |
| `POST` | `/problems/{id}/submit` | Submit code for grading against **all** test cases. | Student |
| `GET` | `/problems/{id}/submissions` | Get the current user's submissions for a problem. | Student |
| `GET` | `/problems/{id}/submissions/all` | Get all student submissions for a problem (gradebook). | Instructor |
| `GET` | `/submissions/{id}` | Get detailed results for a specific submission. | Owner/Instructor |

### WebSocket
| Endpoint | Description |
|---|---|
| `WS /ws/submissions/{submission_id}` | Real-time status updates for a submission (`queued` → `running` → `completed`). |

---

## 🐳 Docker Architecture — Detailed

### `docker-compose.yml` Services

```yaml
services:
  # ── Module 1: Frontend + API ──────────────────────────
  web:
    build: ./frontend
    ports: ["80:80"]
    depends_on: [api]

  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://dockgrade:password@db:5432/dockgrade
      - REDIS_URL=redis://redis:6379/0
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # Access host Docker daemon
      - submissions:/app/submissions                # Shared submission storage
    depends_on: [db, redis]

  # ── Module 2: Job Queue ───────────────────────────────
  redis:
    image: redis:7-alpine
    # No ports exposed to host — internal network only
    volumes:
      - redis_data:/data

  worker:
    build: ./backend
    command: celery -A app.worker worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql+asyncpg://dockgrade:password@db:5432/dockgrade
      - REDIS_URL=redis://redis:6379/0
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - submissions:/app/submissions
    depends_on: [db, redis]

  # ── Module 4: Database ───────────────────────────────
  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=dockgrade
      - POSTGRES_USER=dockgrade
      - POSTGRES_PASSWORD=password
    volumes:
      - pg_data:/var/lib/postgresql/data  # Named volume for persistence

  # ── Monitoring Stack ──────────────────────────────────
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    volumes:
      - grafana_data:/var/lib/grafana

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    ports: ["8080:8080"]

volumes:
  pg_data:
  redis_data:
  grafana_data:
  submissions:

networks:
  default:
    name: dockgrade_network
    driver: bridge
```

### Module 3: Sandbox Execution — How It Works

The Celery worker (running inside the `worker` container) communicates with the **host Docker daemon** via the mounted Docker socket. When a grading task arrives, it does the following:

#### Step-by-step Execution Flow

```python
# Pseudocode for the sandbox execution logic

def execute_submission(submission_id):
    submission = db.get(submission_id)
    problem = db.get(submission.problem_id)
    test_cases = db.get_test_cases(problem.id)

    # 1. Select the base image based on language
    image = {
        "java": "dockgrade-sandbox-java",    # Custom image with JDK
        "python": "dockgrade-sandbox-python"  # Custom image with Python 3
    }[submission.language]

    results = []

    for test_case in test_cases:
        # 2. Create an ephemeral container
        container = docker.create_container(
            image=image,
            command=build_run_command(submission.language, submission.source_code),
            stdin_open=True,

            # 3. Security hardening
            mem_limit="128m",          # Memory cap
            cpu_quota=50000,           # 0.5 CPU
            network_disabled=True,     # No network access
            read_only=True,            # Read-only filesystem
            cap_drop=["ALL"],          # Drop all Linux capabilities
            security_opt=["no-new-privileges"],

            # 4. Tmpfs for writable temp space (in-memory, no disk)
            tmpfs={"/tmp": "size=32m,noexec"}
        )

        # 5. Start and feed input
        container.start()
        container.send_input(test_case.input_data)

        # 6. Wait with timeout
        exit_code = container.wait(timeout=problem.time_limit_sec)

        # 7. Capture output
        stdout = container.logs(stdout=True)
        stderr = container.logs(stderr=True)

        # 8. Compare output
        passed = normalize(stdout) == normalize(test_case.expected_output)

        results.append({
            "test_case_id": test_case.id,
            "passed": passed,
            "actual_output": stdout,
            "expected_output": test_case.expected_output,
            "error": stderr if exit_code != 0 else None,
            "execution_time_ms": measured_time
        })

        # 9. Cleanup (container auto-removed)
        container.remove(force=True)

    # 10. Calculate score and save
    passed_count = sum(1 for r in results if r["passed"])
    submission.score = passed_count
    submission.total_cases = len(results)
    submission.passed_cases = passed_count
    submission.results_json = results
    submission.status = "completed"
    db.save(submission)

    # 11. Notify via WebSocket
    ws.notify(submission.id, submission.status, results)
```

### Sandbox Container Images

Custom lightweight images built specifically for code execution:

**`dockgrade-sandbox-python`** (Dockerfile):
```dockerfile
FROM python:3.12-slim
RUN useradd -m -s /bin/sh runner
USER runner
WORKDIR /code
# No pip installs — standard library only
```

**`dockgrade-sandbox-java`** (Dockerfile):
```dockerfile
FROM eclipse-temurin:21-jdk-alpine
RUN adduser -D -s /bin/sh runner
USER runner
WORKDIR /code
# JDK only — no external dependencies
```

### Container Security Profile

| Security Measure | Configuration | Purpose |
|---|---|---|
| **Memory limit** | `--memory=128m` | Prevents memory exhaustion / OOM on host. |
| **CPU limit** | `--cpus=0.5` | Prevents CPU starvation of other containers. |
| **Execution timeout** | 5–10 seconds (configurable per problem) | Kills infinite loops and runaway processes. |
| **Network disabled** | `--network=none` | Prevents internet access, data exfiltration, or attacks. |
| **Read-only filesystem** | `--read-only` | Prevents writing to the container filesystem. |
| **Tmpfs for /tmp** | `--tmpfs /tmp:size=32m,noexec` | Provides small writable temp space (in-memory only, not persisted). |
| **Capability drop** | `--cap-drop=ALL` | Removes all Linux kernel capabilities (no mount, no network config, etc). |
| **No new privileges** | `--security-opt=no-new-privileges` | Prevents privilege escalation via setuid/setgid binaries. |
| **Non-root user** | `USER runner` in Dockerfile | Code runs as unprivileged user inside the container. |
| **Auto-removal** | `--rm` or explicit `container.remove()` | No residual containers left on the host. |

---

## 📁 Project Structure

```
dockgrade/
├── docker-compose.yml              # Orchestrates all services
├── .env                             # Environment variables (not committed)
├── .env.example                     # Template for environment variables
│
├── frontend/                        # Module 1: React frontend
│   ├── Dockerfile                   # Multi-stage build (build → Nginx serve)
│   ├── nginx.conf                   # Reverse proxy config
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx                 # App entry point
│   │   ├── App.tsx                  # Root router
│   │   ├── api/                     # API client (Axios/fetch wrappers)
│   │   ├── components/              # Reusable UI components
│   │   │   ├── CodeEditor.tsx       # Monaco Editor wrapper
│   │   │   ├── TestCasePanel.tsx    # Test case results display
│   │   │   ├── ProblemDescription.tsx
│   │   │   └── ...
│   │   ├── pages/                   # Route-level page components
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── CoursePage.tsx
│   │   │   ├── ProblemPage.tsx      # The main coding interface
│   │   │   └── GradebookPage.tsx
│   │   ├── hooks/                   # Custom React hooks
│   │   │   ├── useWebSocket.ts      # Submission status listener
│   │   │   └── useAuth.ts
│   │   └── types/                   # TypeScript type definitions
│   └── public/
│
├── backend/                         # Modules 2 & 3: API + Worker
│   ├── Dockerfile                   # Python app image
│   ├── requirements.txt
│   ├── alembic/                     # Database migrations
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # Settings (from env vars)
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── course.py
│   │   │   ├── problem.py
│   │   │   ├── test_case.py
│   │   │   └── submission.py
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── course.py
│   │   │   ├── problem.py
│   │   │   └── submission.py
│   │   ├── routers/                 # API route handlers
│   │   │   ├── auth.py
│   │   │   ├── courses.py
│   │   │   ├── problems.py
│   │   │   └── submissions.py
│   │   ├── services/                # Business logic layer
│   │   │   ├── auth_service.py
│   │   │   ├── course_service.py
│   │   │   └── submission_service.py
│   │   ├── worker/                  # Celery task definitions
│   │   │   ├── celery_app.py        # Celery configuration
│   │   │   ├── tasks.py             # Grading task entry point
│   │   │   └── sandbox.py           # Docker sandbox execution logic
│   │   ├── websocket/               # WebSocket handlers
│   │   │   └── submissions_ws.py
│   │   ├── db.py                    # Database session management
│   │   └── dependencies.py          # FastAPI dependency injection
│   └── tests/
│       ├── test_auth.py
│       ├── test_submissions.py
│       └── ...
│
├── sandbox/                         # Sandbox container images
│   ├── python/
│   │   └── Dockerfile               # dockgrade-sandbox-python
│   └── java/
│       └── Dockerfile               # dockgrade-sandbox-java
│
├── monitoring/                      # Monitoring stack configs
│   ├── prometheus.yml               # Prometheus scrape config
│   ├── grafana/
│   │   └── dashboards/              # Pre-configured Grafana dashboards
│   └── alerting/                    # Alert rules (optional)
│
└── artifiacts/                      # Project documentation
    ├── project-proposal.md          # Semester scope proposal
    ├── full-project-proposal.md     # Full vision proposal
    └── technical-details.md         # This document
```

---

## 🖥️ Key Frontend Views

### 1. Problem Page (The Main Coding Interface)

The core UI — a split-pane layout similar to LeetCode:

```
┌─────────────────────────────────┬──────────────────────────────────┐
│                                 │                                  │
│   Problem Description           │   Code Editor (Monaco)           │
│                                 │                                  │
│   ┌───────────────────────┐     │   Language: [Java ▼]             │
│   │ Two Sum               │     │   ┌────────────────────────────┐ │
│   │                       │     │   │ class Solution {           │ │
│   │ Given an array of     │     │   │   public int[] twoSum(     │ │
│   │ integers nums and an  │     │   │     int[] nums, int target │ │
│   │ integer target, return│     │   │   ) {                      │ │
│   │ indices of the two    │     │   │     // your code here      │ │
│   │ numbers that add up   │     │   │   }                        │ │
│   │ to target.            │     │   │ }                          │ │
│   │                       │     │   │                            │ │
│   │ Constraints:          │     │   │                            │ │
│   │ • 2 ≤ nums.length     │     │   │                            │ │
│   │ • -10⁹ ≤ nums[i]     │     │   └────────────────────────────┘ │
│   └───────────────────────┘     │                                  │
│                                 │   [▶ Run]          [Submit ✓]    │
├─────────────────────────────────┴──────────────────────────────────┤
│   Test Results                                                     │
│   ┌──────────────────────────────────────────────────────────────┐ │
│   │ Test Case 1  ✅ Passed    Input: [2,7,11,15], 9              │ │
│   │                           Expected: [0,1]  Output: [0,1]     │ │
│   │ Test Case 2  ✅ Passed    Input: [3,2,4], 6                  │ │
│   │                           Expected: [1,2]  Output: [1,2]     │ │
│   │ Test Case 3  🔒 Hidden   ✅ Passed                           │ │
│   │ Test Case 4  🔒 Hidden   ❌ Failed                           │ │
│   │                                                               │ │
│   │ Score: 3/4 (75%)                         Time: 142ms          │ │
│   └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

### 2. Dashboard
- Student: list of enrolled courses, recent submissions, overall progress.
- Instructor: list of owned courses, recent student activity, quick links.

### 3. Course Page
- Problem list with difficulty badges and completion status.
- Instructor: add/edit/delete problems, view class gradebook.

### 4. Gradebook
- Table: Student × Problem matrix showing scores.
- Instructor can click into any cell to see the student's code and test case results.

---

## 🔐 Authentication & Authorization

| Concern | Implementation |
|---|---|
| **Password storage** | bcrypt hashed, never stored in plaintext. |
| **Token format** | JWT with short-lived access tokens (15 min) + long-lived refresh tokens (7 days). |
| **Role-based access** | Middleware checks `user.role` and `enrollment.role` before granting access to endpoints. |
| **Course isolation** | Students can only access problems/submissions in courses they're enrolled in. |
| **Instructor verification** | Only the course creator (or TAs) can create/edit problems and view all submissions. |

---

## ⚡ Real-time Flow (WebSocket)

```
Student clicks "Submit"
       │
       ▼
POST /api/v1/problems/{id}/submit
       │
       ▼
API creates submission (status: "queued"), pushes Celery task, returns submission_id
       │
       ▼
Frontend opens WebSocket: ws://host/ws/submissions/{submission_id}
       │
       ▼
Celery worker picks up task → updates status to "running" → pushes via WebSocket
       │
       ▼
Worker executes code per test case → pushes incremental results via WebSocket
       │
       ▼
Worker finishes → updates status to "completed" → pushes final score via WebSocket
       │
       ▼
Frontend renders results in real-time as they arrive
```

---

## 🚀 Development & Deployment

### Local Development
```bash
# Start everything
docker compose up -d --build

# Build sandbox images (one-time)
docker build -t dockgrade-sandbox-python ./sandbox/python
docker build -t dockgrade-sandbox-java ./sandbox/java

# Run database migrations
docker compose exec api alembic upgrade head

# View logs
docker compose logs -f api worker

# Access the app
# Frontend:  http://localhost
# API docs:  http://localhost:8000/docs (Swagger)
# Grafana:   http://localhost:3000
# Prometheus: http://localhost:9090
```

### Environment Variables
```env
# Database
DATABASE_URL=postgresql+asyncpg://dockgrade:password@db:5432/dockgrade

# Redis
REDIS_URL=redis://redis:6379/0

# Auth
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Sandbox defaults
SANDBOX_MEMORY_LIMIT=128m
SANDBOX_CPU_LIMIT=0.5
SANDBOX_DEFAULT_TIMEOUT=10
SANDBOX_TMPFS_SIZE=32m

# Docker
DOCKER_HOST=unix:///var/run/docker.sock
```

---

## 🧪 Testing Strategy

| Level | What | Tools |
|---|---|---|
| **Backend unit tests** | Service logic, schema validation, utility functions. | pytest + pytest-asyncio |
| **API integration tests** | Full request/response cycle against a test database. | pytest + httpx (FastAPI TestClient) |
| **Sandbox tests** | Verify container creation, execution, output capture, timeout handling, and cleanup. | pytest + docker-py against a live Docker daemon |
| **Frontend tests** | Component rendering, user interactions, API mocking. | Vitest + React Testing Library |
| **End-to-end tests** | Full flow: login → open problem → write code → submit → see results. | Playwright |

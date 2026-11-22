# CodeForge

[![Status](https://img.shields.io/badge/Status-Final%20Jury%20Ready-success.svg)](https://github.com)
[![Tests](https://img.shields.io/badge/Tests-145%2F145%20Passing-brightgreen.svg)](https://github.com)
[![Languages](https://img.shields.io/badge/Sandboxes-Python%20%7C%20Java%20%7C%20C%20%7C%20C%2B%2B-blue.svg)](https://github.com)
[![Docker](https://img.shields.io/badge/Docker-Containers%20%26%20Compose-2496ED.svg)](https://docker.com)

**CodeForge** is an enterprise-grade automated programming judge, learning management system (LMS), and proctored assessment platform built for computer science education. It enables students to learn programming concepts, solve algorithmic challenges in the browser, and take locked-down proctored exams — while executing untrusted code inside ephemeral, hardened Docker sandbox containers.

---

## 🌟 Key Platform Features

- **Multi-Language Sandboxing:** Securely compile and execute **Python 3.12**, **Java 21**, **C (GCC 13 / C11)**, and **C++ (G++ 20 / C++20)** inside isolated ephemeral containers.
- **Real-Time WebSocket Streaming:** Instantaneous live test progression (`Queued → Compiling → Running N/M → Completed`) streamed via FastAPI WebSockets and Redis Pub/Sub — eliminating polling lag.
- **Proctored Assessment & Anti-Cheat Engine:** Locked-down exam environments with full-screen enforcement, tab-switch detection and violation logging, clipboard paste blocking, and automated timer-based submission.
- **Interactive Learning Modules:** Structured curricula with rich Markdown theory, embedded YouTube video lectures, sequential module unlocking, and inline practice challenges.
- **Performance Analytics Dashboard:** Class-wide KPIs, interactive pass rate distributions, 7-day submission volume trends, per-student progress timelines, and common error categorizations.
- **Advanced Grading & Custom Stdin:** Weighted test cases with partial credit scoring and sandboxed arbitrary stdin execution with rate limiting.
- **Lab Sessions & Gamified Badges:** Live instructor monitoring dashboards and badge rewards for students who solve problems beyond the mandatory threshold.
- **Production Hardening:** Dropped capabilities, `--pids-limit=64`, `--ulimit nofile=64:64`, read-only roots with 16MB noexec `tmpfs`, automated health/readiness probes, and cross-platform one-command installers.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18 + TypeScript + Vite + TailwindCSS + shadcn/ui |
| **Code Editor** | Monaco Editor (`@monaco-editor/react`) with Vim/Emacs keybindings & auto-save |
| **Backend API** | Python 3.12 + FastAPI + WebSockets + Pydantic v2 |
| **Job Queue & Broker** | Celery 5 + Redis 7 (Task Queue, Pub/Sub, and Token-Bucket Rate Limiter) |
| **Database & ORM** | PostgreSQL 16 + SQLAlchemy 2.0 (Async) + Alembic migrations |
| **Sandbox Execution** | Docker SDK (`docker-py`) with ephemeral GCC, OpenJDK, and Python runtimes |
| **Reverse Proxy** | Nginx (static asset serving, API reverse proxy, and WebSocket upgrades) |
| **Monitoring** | Prometheus + Grafana + cAdvisor |

---

## ⚡ Quick Start

CodeForge includes automated cross-platform installers that detect prerequisites, build all execution sandboxes, run migrations, and seed demo data in a single command.

### Linux / macOS / WSL2
```bash
git clone <repo-url> code-forge
cd code-forge
./codeforge-setup.sh
```
*(Add `--build` to force rebuild application images).*

### Windows PowerShell (Native)
```powershell
powershell -ExecutionPolicy Bypass -File .\codeforge-setup.ps1
```

### Windows Double-Click Launcher
Double-click `codeforge-setup.bat` in File Explorer.

---

## 🌐 Platform Service Map

Once deployed, the platform services are accessible at:

| Service | URL | Default Credentials | Description |
|---|---|---|---|
| **Web Application** | [http://localhost](http://localhost) | See below | Full React single-page app |
| **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | — | Interactive OpenAPI documentation |
| **Grafana Dashboard** | [http://localhost:3000](http://localhost:3000) | `admin` / `admin` | Real-time container metrics & dashboards |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | — | Prometheus query interface |
| **cAdvisor** | [http://localhost:8080](http://localhost:8080) | — | Container resource metrics |

---

## 🔑 Pre-Seeded Demo Accounts

The database comes pre-seeded with instructor and student accounts, the **CS101: Introduction to Programming** course, problems, lab sessions, learning modules, and a proctored midterm exam:

| Role | Email | Password | Details |
|---|---|---|---|
| **Instructor** | `admin@codeforge.local` | `changeme` | Admin Instructor; full management, grading & audit across CS101, CS201, CS301 |
| **Instructor** | `prof.chen@codeforge.local` | `changeme` | Prof. Alan Chen; Algorithms & Discrete Math faculty (CS201, MATH150) |
| **Instructor** | `dr.stone@codeforge.local` | `changeme` | Dr. Elena Stone; Systems Programming faculty (CS301) |
| **Student** | `student@codeforge.local` | `changeme` | "Alex Student" — clean baseline for live coding, badge earning & exams |
| **Student** | `diana@codeforge.local` | `changeme` | "Diana Prince" — Leaderboard leader (4 badges, completed modules, 100% exam) |
| **Student** | `alice@codeforge.local` | `changeme` | "Alice Johnson" — 3 badges earned, exam completed with 1 violation |
| **Student** | `bob@codeforge.local` | `changeme` | "Bob Smith" — 2 badges earned, active exam with 2 violations |
| **Student** | `kevin@codeforge.local` | `changeme` | "Kevin Mitnick" — Systems hacker (CS301 exam 100% with violations) |
| **Student** | `evan@, fiona@, george@, hannah@, ian@, julia@, charlie@` | `changeme` | Additional students enrolled across courses & labs |

*Course Invite Codes:* `CS101A` (CS101), `CS201B` (CS201), `CS301C` (CS301), `M150D` (MATH150)

---

## 📁 Repository Structure

```
code-forge/
├── codeforge-setup.sh         # Cross-platform setup script (Linux, macOS, WSL2)
├── codeforge-setup.ps1        # Turnkey installer for Windows PowerShell
├── codeforge-setup.bat        # Windows double-click launcher
├── docker-compose.yml         # Container orchestration (web, api, worker, db, redis, monitoring)
├── .env.example               # Environment variables configuration template
├── backend/                   # FastAPI backend & Celery worker
│   ├── app/
│   │   ├── main.py            # App initialization, CORS, health probes & router mounts
│   │   ├── config.py          # Pydantic settings & sandbox security parameters
│   │   ├── db.py              # Async SQLAlchemy engine & session factory
│   │   ├── models/            # SQLAlchemy 2.0 ORM models (Auth, Courses, Exams, Modules, etc.)
│   │   ├── schemas/           # Pydantic validation schemas
│   │   ├── routers/           # API endpoints (Auth, Courses, Labs, Modules, Exams, Analytics)
│   │   ├── websocket/         # Real-time WebSocket submission streaming (Redis Pub/Sub)
│   │   ├── worker/            # Celery worker, tasks, and Docker sandbox executor
│   │   └── seed.py            # Demo database seeder
│   ├── tests/                 # Automated test suite (145 tests)
│   └── manage.py              # CLI management tool (load-problems, seed)
├── frontend/                  # React 18 + Vite + TypeScript frontend
│   ├── src/
│   │   ├── components/        # Monaco Editor, Navbar, Command Palette, TestCasePanel
│   │   ├── pages/             # Route pages (Learn, Exam, Analytics, Labs, Editor, etc.)
│   │   ├── hooks/             # WebSocket and Poller hooks
│   │   └── api/client.ts      # Axios API client with automatic token refreshing
├── sandbox/                   # Multi-language sandbox Dockerfiles
│   ├── python/                # Python 3.12-slim sandbox image
│   ├── java/                  # Eclipse Temurin OpenJDK 21 sandbox image
│   ├── c/                     # Alpine GCC 13 sandbox image
│   └── cpp/                   # Alpine G++ 20 sandbox image
├── problems/                  # YAML-defined coding problem library
│   ├── hello-world/
│   ├── two-sum/
│   ├── reverse-string/
│   └── fizzbuzz/
├── monitoring/                # Prometheus and Grafana dashboards configuration
└── artifacts/                 # Architecture specifications & operational documentation
    ├── how-to-run.md          # Complete How-To-Run & Final Jury demonstration guide
    ├── backend-architecture.md# Complete backend architecture specification
    ├── frontend.md            # Frontend architecture & route map
    ├── api-contracts.md       # API contract reference
    ├── operations.md          # Operations runbook & administrative commands
    ├── backup-and-recovery.md # Backup, restore, and disaster recovery guide
    └── final-jury-implemenattion_plan.md # Master Final Jury implementation plan
```

---

## 🧪 Automated Testing

CodeForge maintains a 100% test pass rate across 149 automated tests verifying every subsystem:

```bash
# Run all tests in the API container
docker compose run --rm api pytest -v

# Run domain-specific suites
docker compose run --rm api pytest tests/test_security.py -v     # Sandbox containment (fork bombs, limits)
docker compose run --rm api pytest tests/test_exams.py -v        # Proctored exams & anti-cheat logging
docker compose run --rm api pytest tests/test_modules.py -v      # Learning modules curriculum & progress
docker compose run --rm api pytest tests/test_analytics.py -v    # Course & problem analytics
docker compose run --rm api pytest tests/test_websocket.py -v    # Real-time WebSocket streaming
docker compose run --rm api pytest tests/test_sandbox_cpp.py -v  # C and C++ compilation & execution
docker compose run --rm api pytest tests/test_custom_input.py -v # Arbitrary stdin runner
```

---

## 🔒 Security Architecture

User code is executed inside ephemeral, disposable Docker containers with strict security boundaries:
- **No Network:** `network_disabled=True` eliminates external communication and SSRF.
- **Process Bomb Defense:** `--pids-limit=64` strictly limits process trees, preventing fork bombs.
- **File Descriptor Limits:** `--ulimit nofile=64:64` prevents OS descriptor exhaustion.
- **Memory & CPU Caps:** 128MB RAM limit with OOM termination and 0.5 CPU quota cap.
- **Privilege Lockdown:** `cap_drop=["ALL"]`, `no-new-privileges`, and non-root `runner` user.
- **Constrained Filesystem:** Read-only root filesystem with a 16MB `noexec,nosuid` `tmpfs` mount at `/tmp`.

For detailed operations, recovery, and architecture guides, consult the documents in the [`artifacts/`](./artifacts/) directory.

# CodeForge — Operations Runbook

Quick reference for setting up, running, testing, restarting, and tearing down the CodeForge stack.

---

## 🗺️ Service Map

| Container | Role | Port / URL | Health Check |
|---|---|---|---|
| `web` | Nginx — serves React frontend, proxies `/api/*` and `/ws/*` | http://localhost:80 | HTTP GET `/` |
| `api` | FastAPI — REST API, WebSockets, Swagger docs | http://localhost:8000 (docs: `/docs`) | HTTP GET `/health/ready` |
| `worker` | Celery — Python, Java, C, and C++ sandbox grading engine | — | Celery ping |
| `db` | PostgreSQL 16 — persistent relational data store | localhost:5432 | `pg_isready` |
| `redis` | Redis 7 — task queue broker, Pub/Sub channel & rate limiter | localhost:6379 | `redis-cli ping` |
| `prometheus` | Prometheus metrics collection | http://localhost:9090 | HTTP GET `/-/healthy` |
| `grafana` | Live infrastructure dashboards | http://localhost:3000 (admin / admin) | HTTP GET `/api/health` |
| `cadvisor` | Container resource stats (CPU, memory, IO) | http://localhost:8080 | HTTP GET `/healthz` |

---

## ⚡ Quick Turnkey Setup (Recommended)

CodeForge provides automated, single-command cross-platform installer scripts that verify Docker, configure environment variables, build all 4 sandbox images, run database migrations, and seed demo data:

### On Linux, macOS, or Windows WSL2:
```bash
./codeforge-setup.sh
```
*(Use `./codeforge-setup.sh --build` to force rebuild application images).*

### On Windows PowerShell (Native):
```powershell
powershell -ExecutionPolicy Bypass -File .\codeforge-setup.ps1
```

### On Windows CMD / File Explorer:
Double-click `codeforge-setup.bat`.

---

## 🛠️ Manual First-Time Setup

If setting up step-by-step manually:

```bash
# 1. Copy environment variables
cp .env.example .env

# 2. Build the 4 execution sandbox images (only needed once or after sandbox changes)
docker build -t codeforge-sandbox-python ./sandbox/python
docker build -t codeforge-sandbox-java ./sandbox/java
docker build -t codeforge-sandbox-c ./sandbox/c
docker build -t codeforge-sandbox-cpp ./sandbox/cpp

# 3. Start all services
docker compose up -d --build

# 4. Apply database migrations
docker compose exec api alembic upgrade head

# 5. Seed the database with demo courses, problems, modules, exams, and users
docker compose exec api python manage.py seed
```

---

## 🔑 Default Demo Credentials

| Role | Email | Password | Pre-seeded Context |
|---|---|---|---|
| **Instructor** | `admin@codeforge.local` | `changeme` | Creator of CS101, all problems, lab sessions, learning modules, exams |
| **Student (Hero)**| `student@codeforge.local`| `changeme` | "Alex Student" — ready for live grading, lab badge, and exam demos |
| **Student** | `diana@codeforge.local` | `changeme` | "Diana Prince" — Top leaderboard scorer (3 badges) |
| **Student** | `alice@codeforge.local` | `changeme` | "Alice Johnson" — 2 badges earned |
| **Student** | `bob@codeforge.local`   | `changeme` | "Bob Smith" — 1 badge earned |
| **Student** | `charlie@codeforge.local` | `changeme` | "Charlie Brown" — Baseline student |

---

## 🔄 Daily Start / Stop

```bash
# Start all services in background
docker compose up -d

# Stop all services (preserves database & volume data)
docker compose down

# Stop and wipe ALL data volumes (clean reset)
docker compose down -v
```

---

## 🔨 Rebuild After Code Changes

```bash
# Backend code change (FastAPI or Celery worker)
docker compose up -d --build api worker

# Frontend code change (React UI)
docker compose up -d --build web

# Rebuild all application services
docker compose up -d --build
```

---

## 🧪 Running Automated Tests

CodeForge includes an extensive automated test suite covering authentication, courses, gradebook, lab sessions, badges, learning modules, proctored exams, anti-cheat tracking, analytics, custom stdin runner, and sandbox security isolation:

```bash
# Run the complete test suite (145 tests)
docker compose run --rm api pytest -v

# Run specific domain test suites
docker compose run --rm api pytest tests/test_security.py -v       # Sandbox security hardening & limits
docker compose run --rm api pytest tests/test_exams.py -v          # Proctored exams & violation logging
docker compose run --rm api pytest tests/test_modules.py -v        # Learning modules & curriculum
docker compose run --rm api pytest tests/test_analytics.py -v      # Course & problem analytics
docker compose run --rm api pytest tests/test_websocket.py -v      # Real-time WebSocket streaming
docker compose run --rm api pytest tests/test_sandbox_cpp.py -v    # C and C++ compilation & execution
docker compose run --rm api pytest tests/test_custom_input.py -v   # Sandboxed arbitrary stdin runner
```

---

## 🩺 Health & Readiness Monitoring

```bash
# Liveness probe
curl -s http://localhost:8000/health | jq .

# Readiness probe (verifies database & Redis connectivity)
curl -s http://localhost:8000/health/ready | jq .

# Inspect running container health status
docker compose ps
```

---

## 📋 Problem Management

Problems are defined in YAML format under `./problems/<slug>/`:

```bash
# Load all YAML problems into the database
docker compose exec api python manage.py load-problems ./problems/

# Load a specific single problem
docker compose exec api python manage.py load-problems ./problems/two-sum/
```

---

## 🔍 Log Inspection

```bash
# Stream API & Worker logs together
docker compose logs -f api worker

# Inspect last 100 lines of worker logs
docker compose logs --tail=100 worker

# Check database connection logs
docker compose logs db
```

---

## 🛡️ Sandbox Verification

Check that no orphaned or zombie sandbox containers linger after code runs:

```bash
docker ps --filter "name=codeforge-sandbox"
```
*(Should show 0 containers when idle).*

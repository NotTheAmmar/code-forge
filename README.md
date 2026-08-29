# CodeForge

A browser-based competitive programming judge — open a problem, write Java code, execute it in an ephemeral Docker sandbox, and see test-case results instantly.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + TypeScript |
| Code Editor | Monaco Editor (`@monaco-editor/react`) |
| Styling | TailwindCSS + shadcn/ui |
| Backend API | Python 3.12 + FastAPI |
| Job Queue | Celery + Redis |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 + Alembic |
| Sandbox | Docker (`docker-py`) |
| Reverse Proxy | Nginx |
| Monitoring | Prometheus + Grafana + cAdvisor |

---

## Quick Start

### Prerequisites
- Docker 24+ and Docker Compose v2
- Git

### 1. Clone and configure

```bash
git clone <repo-url> code-forge
cd code-forge
cp .env.example .env
```

### 2. Build the Java sandbox image *(one-time)*

```bash
docker build -t codeforge-sandbox-java ./sandbox/java
```

### 3. Start all services

```bash
docker compose up -d --build
```

### 4. Run database migrations *(one-time)*

```bash
docker compose exec api alembic upgrade head
```

### 5. Load sample problems *(one-time)*

```bash
docker compose exec api python manage.py load-problems ./problems/
```

### 6. Open the app

| Service | URL |
|---|---|
| App | http://localhost |
| API Docs (Swagger) | http://localhost:8000/docs |
| Grafana | http://localhost:3000 (admin/admin) |
| Prometheus | http://localhost:9090 |
| cAdvisor | http://localhost:8080 |

---

## Project Structure

```
code-forge/
├── docker-compose.yml
├── .env.example
├── frontend/          # React + Vite frontend
├── backend/           # FastAPI API + Celery worker
├── sandbox/           # Sandbox container Dockerfiles
│   └── java/
├── problems/          # YAML-defined coding problems
│   ├── hello-world/
│   ├── two-sum/
│   └── fizzbuzz/
├── monitoring/        # Prometheus + Grafana config
└── artifiacts/        # Project docs
    ├── operations.md          # ← Ops runbook (setup/deploy/reset)
    ├── backend-architecture.md
    └── ta-1-implementation_plan.md
```

---

## Problem Authoring

Problems live in the `problems/` directory as YAML + Markdown files:

```bash
# Load all problems into the database
docker compose exec api python manage.py load-problems ./problems/

# Idempotent — safe to re-run after edits
```

See [`problems/hello-world/`](./problems/hello-world/) for a complete example.

---

## Development

```bash
# View logs
docker compose logs -f api worker

# Restart a single service
docker compose restart api

# Rebuild after code changes
docker compose up -d --build api worker

# Run tests
docker compose exec api pytest tests/test_api.py -v
```

For full operations reference (teardown, data reset, troubleshooting), see [`artifiacts/operations.md`](./artifiacts/operations.md).

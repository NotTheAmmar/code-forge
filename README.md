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

---

## Quick Start

### Prerequisites
- Docker 24+ and Docker Compose v2
- Node 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings (defaults work for local dev)
```

### 2. Build sandbox images (one-time)

```bash
docker build -t codeforge-sandbox-java ./sandbox/java
```

### 3. Start all services

```bash
docker compose up -d --build
```

### 4. Run database migrations

```bash
docker compose exec api alembic upgrade head
```

### 5. Load sample problems

```bash
docker compose exec api python manage.py load-problems ./problems/
```

### 6. Open the app

| Service | URL |
|---|---|
| App | http://localhost |
| API Docs (Swagger) | http://localhost:8000/docs |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

---

## Project Structure

```
codeforge/
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
└── monitoring/        # Prometheus + Grafana config
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
docker compose up -d --build api
```

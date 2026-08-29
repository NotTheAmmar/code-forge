# CodeForge — Operations Runbook

Quick reference for setting up, running, restarting, and tearing down the CodeForge stack.

---

## Service Map

| Container | Role | URL |
|---|---|---|
| `web` | Nginx — serves React frontend, proxies `/api/*` | http://localhost |
| `api` | FastAPI — REST API + Swagger docs | http://localhost:8000/docs |
| `worker` | Celery — Java sandbox execution engine | — |
| `db` | PostgreSQL 16 — persistent data store | localhost:5432 |
| `redis` | Redis 7 — task queue broker | localhost:6379 |
| `prometheus` | Metrics collection | http://localhost:9090 |
| `grafana` | Dashboards | http://localhost:3000 |
| `cadvisor` | Container resource stats | http://localhost:8080 |

---

## First-Time Setup

Run these **once** on a fresh clone. Order matters.

```bash
# 1. Copy environment config (defaults work for local dev)
cp .env.example .env

# 2. Build the Java sandbox image
#    Separate from docker compose — only needed once (or after sandbox changes)
docker build -t codeforge-sandbox-java ./sandbox/java

# 3. Build and start all services
docker compose up -d --build

# 4. Run database migrations
docker compose exec api alembic upgrade head

# 5. Load sample problems into the database
docker compose exec api python manage.py load-problems ./problems/

# 6. Open the app
#    http://localhost            → frontend
#    http://localhost:8000/docs  → Swagger UI
```

> **Note:** Steps 4 and 5 are only needed on first run (or after resetting the database). They are idempotent — safe to re-run.

---

## Daily Start / Stop

```bash
# Start all services (no rebuild)
docker compose up -d

# Stop all services (preserves data volumes)
docker compose down

# Stop AND remove all data (full reset)
docker compose down -v
```

---

## Rebuild After Code Changes

Only rebuild the service(s) you changed — faster than rebuilding everything.

```bash
# Rebuild and restart backend (API + worker share the same image)
docker compose up -d --build api worker

# Rebuild and restart frontend only
docker compose up -d --build web

# Rebuild everything
docker compose up -d --build
```

> **Tip:** The sandbox image (`codeforge-sandbox-java`) is **not** part of `docker compose` — rebuild it manually when `./sandbox/java/Dockerfile` changes:
> ```bash
> docker build -t codeforge-sandbox-java ./sandbox/java
> ```

---

## Restart a Service

```bash
docker compose restart api
docker compose restart worker
docker compose restart web
```

---

## Reset / Wipe Data

```bash
# Wipe the database only (keeps other volumes)
docker compose down
docker volume rm code-forge_pg_data
docker compose up -d
docker compose exec api alembic upgrade head
docker compose exec api python manage.py load-problems ./problems/

# Full wipe — removes ALL volumes (db, redis, grafana data)
docker compose down -v
# Then redo First-Time Setup steps 3–5
```

---

## Add / Update Problems

Problems live in `./problems/<slug>/`. Each folder needs:
- `problem.yaml` — title, difficulty, limits
- `description.md` — problem statement (markdown)
- `tests/01.in`, `tests/01.out`, etc.

```bash
# After adding or editing a problem file:
docker compose exec api python manage.py load-problems ./problems/

# Load a single problem
docker compose exec api python manage.py load-problems ./problems/two-sum/
```

The loader is **idempotent** — re-running it updates existing problems and adds new ones without dropping data.

---

## View Logs

```bash
# Follow all logs
docker compose logs -f

# Follow specific services
docker compose logs -f api worker

# Last 50 lines, no follow
docker compose logs --tail=50 worker
```

---

## Run Tests

```bash
# Fast API tests (SQLite in-memory, no Docker needed) — ~1s
docker compose exec api pytest tests/test_api.py -v

# Normalize unit tests — <1s
docker compose exec api pytest tests/test_sandbox.py::TestNormalize -v

# Sandbox integration tests (requires codeforge-sandbox-java image) — ~30s
docker compose exec api pytest tests/test_sandbox.py -v -s -m sandbox
```

---

## Database Migrations

```bash
# Apply all pending migrations
docker compose exec api alembic upgrade head

# Check current migration version
docker compose exec api alembic current

# Generate a new migration after changing ORM models
docker compose exec api alembic revision --autogenerate -m "describe_your_change"
# Review and commit the generated file in backend/alembic/versions/
```

---

## Monitoring

| Service | URL | Default Login |
|---|---|---|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| cAdvisor | http://localhost:8080 | — |

Prometheus scrapes:
- `api:8000/metrics` — FastAPI request metrics (via `prometheus-fastapi-instrumentator`)
- `cadvisor:8080` — container CPU/memory/network stats

---

## Troubleshooting

### API returns 502 / frontend can't reach backend
```bash
docker compose ps                    # check all services are "Up"
docker compose logs api --tail=30    # look for startup errors
```

### Worker not processing submissions (status stuck at "queued")
```bash
docker compose logs worker --tail=30
docker compose exec worker celery -A app.worker.celery_app inspect active
```

### Sandbox fails with Docker permission error
The worker container needs access to the Docker socket. Verify:
```bash
docker compose exec worker docker ps   # should list running containers
```
If that fails, check `/var/run/docker.sock` permissions on the host:
```bash
ls -la /var/run/docker.sock
# Should be srw-rw---- or similar; add your user to the 'docker' group if needed
sudo usermod -aG docker $USER && newgrp docker
```

### Migrations not applying / table not found
```bash
docker compose exec api alembic current    # see what's applied
docker compose exec api alembic upgrade head
```

### Problems not showing in the UI
```bash
docker compose exec api python manage.py load-problems ./problems/
curl http://localhost:8000/api/v1/problems   # should return JSON array
```

### Prometheus shows "api" target as DOWN
Verify the metrics endpoint is reachable:
```bash
curl http://localhost:8000/metrics | head -20
```

---

## Useful One-Liners

```bash
# Check all container health
docker compose ps

# See resource usage
docker stats --no-stream

# Count active sandbox containers (should be 0 when idle)
docker ps --filter ancestor=codeforge-sandbox-java --format '{{.Names}}'

# Quick API smoke test
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/api/v1/problems | python3 -m json.tool
```

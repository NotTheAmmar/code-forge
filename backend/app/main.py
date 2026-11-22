import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.routers.ai_tutor import router as ai_tutor_router
from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.courses import router as courses_router
from app.routers.exams import router as exams_router
from app.routers.labs import router as labs_router
from app.routers.modules import router as modules_router
from app.routers.problems import router as problems_router
from app.routers.submissions import router as submissions_router
from app.websocket.submissions_ws import router as ws_router

app = FastAPI(
    title="CodeForge API",
    description="Browser-based competitive programming judge — sandboxed code execution engine.",
    version="0.6.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus metrics (/metrics) ─────────────────────────────────────────────
Instrumentator().instrument(app).expose(app)

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(ai_tutor_router, prefix=API_PREFIX)
app.include_router(analytics_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(courses_router, prefix=API_PREFIX)
app.include_router(exams_router, prefix=API_PREFIX)
app.include_router(labs_router, prefix=API_PREFIX)
app.include_router(modules_router, prefix=API_PREFIX)
app.include_router(problems_router, prefix=API_PREFIX)
app.include_router(submissions_router, prefix=API_PREFIX)
app.include_router(ws_router, prefix=API_PREFIX)
app.include_router(ws_router, prefix="")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness probe — returns OK when the API is up."""
    return {"status": "ok", "service": "codeforge-api"}


@app.get("/health/ready", tags=["meta"])
async def readiness_probe(db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness probe — verifies database and message broker availability."""
    checks = {"database": "disconnected", "redis": "disconnected"}
    is_ready = True

    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        is_ready = False
        checks["database"] = f"error: {str(e)}"

    # Check Redis
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "connected"
    except Exception as e:
        is_ready = False
        checks["redis"] = f"error: {str(e)}"

    if not is_ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=checks)

    return {"status": "ready", "service": "codeforge-api", **checks}

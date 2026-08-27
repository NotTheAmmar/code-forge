from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title="CodeForge API",
    description="Browser-based competitive programming judge — sandboxed code execution engine.",
    version="0.1.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers (registered when implemented) ────────────────────────────────────
# from app.routers import problems, submissions
# app.include_router(problems.router, prefix="/api/v1")
# app.include_router(submissions.router, prefix="/api/v1")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness probe — returns OK when the API is up."""
    return {"status": "ok", "service": "codeforge-api"}

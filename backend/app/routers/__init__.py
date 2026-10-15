"""Routers package."""

from app.routers.auth import router as auth_router
from app.routers.problems import router as problems_router
from app.routers.submissions import router as submissions_router

__all__ = ["auth_router", "problems_router", "submissions_router"]

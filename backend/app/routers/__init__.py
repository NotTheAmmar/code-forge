"""Routers package."""

from app.routers.problems import router as problems_router
from app.routers.submissions import router as submissions_router

__all__ = ["problems_router", "submissions_router"]

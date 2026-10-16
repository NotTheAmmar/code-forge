"""Routers package."""

from app.routers.auth import router as auth_router
from app.routers.courses import router as courses_router
from app.routers.labs import router as labs_router
from app.routers.problems import router as problems_router
from app.routers.submissions import router as submissions_router

__all__ = ["auth_router", "courses_router", "labs_router", "problems_router", "submissions_router"]

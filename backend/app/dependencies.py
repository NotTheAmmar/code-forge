"""FastAPI dependency injection helpers.

Provides:
  - get_db           — yields an async SQLAlchemy session
  - get_current_user — decodes the Bearer JWT and returns the User ORM object
  - require_instructor — raises 403 if user is not an instructor
  - require_enrollment — raises 403 if user is not enrolled in the given course
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db  # re-export for backward compat
from app.models.enrollment import Enrollment
from app.models.user import User
from app.services.auth_service import TokenError, decode_access_token

# ── Bearer scheme ─────────────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=True)


# ── get_current_user ──────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the Bearer JWT and return the corresponding User row.

    Raises HTTP 401 if the token is missing, invalid, or the user no longer exists.
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    try:
        user_id = uuid.UUID(user_id_str)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


# ── Role guard ────────────────────────────────────────────────────────────────

def require_instructor(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that raises HTTP 403 unless the current user is an instructor."""
    if current_user.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can perform this action.",
        )
    return current_user


# ── Enrollment guard ──────────────────────────────────────────────────────────

class RequireEnrollment:
    """Dependency factory — checks that the current user is enrolled in a course.

    Usage::

        @router.get("/{course_id}/problems")
        async def list_problems(
            enrollment: Enrollment = Depends(RequireEnrollment()),
            ...
        )

    The ``course_id`` path parameter is automatically read from the request.
    """

    async def __call__(
        self,
        course_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> Enrollment:
        result = await db.execute(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.user_id == user.id,
            )
        )
        enrollment = result.scalar_one_or_none()
        if enrollment is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this course.",
            )
        return enrollment


require_enrollment = RequireEnrollment()

__all__ = [
    "get_db",
    "get_current_user",
    "require_instructor",
    "require_enrollment",
]

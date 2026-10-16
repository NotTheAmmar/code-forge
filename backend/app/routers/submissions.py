"""FastAPI router for submission-related endpoints.

Endpoints:
    GET /submissions/{id}  → get submission status and results (polling endpoint)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.badge import Badge
from app.models.submission import Submission
from app.models.user import User
from app.schemas.submission import SubmissionResponse

router = APIRouter(prefix="/submissions", tags=["submissions"])


# ── GET /submissions/{id} ─────────────────────────────────────────────────────

@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    """Return the current status and results of a submission.

    Requires authentication. Students may only view their own submissions;
    instructors may view any submission.
    """
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{submission_id}' not found.",
        )

    # Permission check: student owner or instructor
    if submission.user_id is not None and submission.user_id != current_user.id:
        if current_user.role != "instructor":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this submission.",
            )

    badge_awarded = False
    new_badge_count = None

    if submission.lab_session_id and submission.user_id:
        badge_res = await db.execute(
            select(Badge).where(
                Badge.user_id == submission.user_id,
                Badge.lab_session_id == submission.lab_session_id,
                Badge.problem_id == submission.problem_id,
            )
        )
        if badge_res.scalar_one_or_none() is not None:
            badge_awarded = True

        count_res = await db.execute(
            select(func.count(Badge.id)).where(
                Badge.user_id == submission.user_id,
                Badge.lab_session_id == submission.lab_session_id,
            )
        )
        new_badge_count = count_res.scalar_one()

    resp = SubmissionResponse.model_validate(submission)
    resp.badge_awarded = badge_awarded
    resp.new_badge_count = new_badge_count
    return resp

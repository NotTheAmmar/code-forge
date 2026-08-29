"""FastAPI router for submission-related endpoints.

Endpoints:
    GET /submissions/{id}  → get submission status and results (polling endpoint)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.submission import Submission
from app.schemas.submission import SubmissionResponse

router = APIRouter(prefix="/submissions", tags=["submissions"])


# ── GET /submissions/{id} ─────────────────────────────────────────────────────

@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Submission:
    """Return the current status and results of a submission.

    This is the polling endpoint — the frontend calls it every 1–1.5s until
    status is no longer 'queued' or 'running'.
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
    return submission

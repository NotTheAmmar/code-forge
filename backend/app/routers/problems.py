"""FastAPI router for problem-related endpoints.

Endpoints:
    GET  /problems              → list all problems
    GET  /problems/{slug}       → get full problem detail
    POST /problems/{slug}/run   → run code against visible test cases
    POST /problems/{slug}/submit → run code against all test cases
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models.problem import Problem
from app.models.submission import Submission
from app.schemas.problem import ProblemDetail, ProblemSummary
from app.schemas.submission import RunRequest, SubmissionCreated
from app.worker.tasks import grade_submission

router = APIRouter(prefix="/problems", tags=["problems"])


# ── GET /problems ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[ProblemSummary])
async def list_problems(db: AsyncSession = Depends(get_db)) -> list[Problem]:
    """Return all problems as a summary list (no test cases, no description)."""
    result = await db.execute(select(Problem).order_by(Problem.created_at))
    return list(result.scalars().all())


# ── GET /problems/{slug} ──────────────────────────────────────────────────────

@router.get("/{slug}", response_model=ProblemDetail)
async def get_problem(slug: str, db: AsyncSession = Depends(get_db)) -> Problem:
    """Return full problem detail including all test cases and starter code."""
    result = await db.execute(
        select(Problem)
        .where(Problem.slug == slug)
        .options(selectinload(Problem.test_cases))
    )
    problem = result.scalar_one_or_none()
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{slug}' not found.",
        )
    return problem


# ── POST /problems/{slug}/run ─────────────────────────────────────────────────

@router.post("/{slug}/run", response_model=SubmissionCreated, status_code=status.HTTP_202_ACCEPTED)
async def run_code(
    slug: str,
    body: RunRequest,
    db: AsyncSession = Depends(get_db),
) -> SubmissionCreated:
    """Run code against visible test cases only.

    Creates a Submission record (is_full_submit=False), enqueues it for
    execution in the Celery worker, and returns the submission_id immediately.
    """
    problem = await _get_problem_or_404(slug, db)

    submission = Submission(
        id=uuid.uuid4(),
        problem_id=problem.id,
        language=body.language,
        source_code=body.source_code,
        status="queued",
        is_full_submit=False,
    )
    db.add(submission)
    await db.flush()  # assigns the id without committing

    submission_id = str(submission.id)
    await db.commit()

    # Dispatch to Celery worker (non-blocking)
    grade_submission.delay(submission_id)

    return SubmissionCreated(submission_id=submission_id)


# ── POST /problems/{slug}/submit ──────────────────────────────────────────────

@router.post("/{slug}/submit", response_model=SubmissionCreated, status_code=status.HTTP_202_ACCEPTED)
async def submit_code(
    slug: str,
    body: RunRequest,
    db: AsyncSession = Depends(get_db),
) -> SubmissionCreated:
    """Submit code for grading against all test cases (visible + hidden).

    Creates a Submission record (is_full_submit=True), enqueues it for
    execution in the Celery worker, and returns the submission_id immediately.
    """
    problem = await _get_problem_or_404(slug, db)

    submission = Submission(
        id=uuid.uuid4(),
        problem_id=problem.id,
        language=body.language,
        source_code=body.source_code,
        status="queued",
        is_full_submit=True,
    )
    db.add(submission)
    await db.flush()

    submission_id = str(submission.id)
    await db.commit()

    # Dispatch to Celery worker (non-blocking)
    grade_submission.delay(submission_id)

    return SubmissionCreated(submission_id=submission_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_problem_or_404(slug: str, db: AsyncSession) -> Problem:
    result = await db.execute(select(Problem).where(Problem.slug == slug))
    problem = result.scalar_one_or_none()
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{slug}' not found.",
        )
    return problem

"""FastAPI router for problem-related endpoints.

Endpoints:
    GET  /problems              → list all problems (public — kept for backward compat)
    GET  /problems/{slug}       → get full problem detail (public)
    POST /problems/{slug}/run   → run code against visible test cases (auth required)
    POST /problems/{slug}/submit → run code against all test cases (auth required)

Note: Course-scoped problem CRUD lives in app/routers/courses.py.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db, get_current_user
from app.models.lab_session import LabSession, LabSessionProblem
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.schemas.problem import ProblemDetail, ProblemSummary
from app.schemas.submission import (
    RunRequest,
    SubmissionCreated,
    SubmissionSummaryResponse,
    SubmitRequest,
)
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
    current_user: User = Depends(get_current_user),
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
        user_id=current_user.id,
        language=body.language,
        source_code=body.source_code,
        status="queued",
        is_full_submit=False,
    )
    db.add(submission)
    await db.flush()

    submission_id = str(submission.id)
    await db.commit()

    grade_submission.delay(submission_id)
    return SubmissionCreated(submission_id=submission_id)


# ── POST /problems/{slug}/submit ──────────────────────────────────────────────

@router.post("/{slug}/submit", response_model=SubmissionCreated, status_code=status.HTTP_202_ACCEPTED)
async def submit_code(
    slug: str,
    body: SubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionCreated:
    """Submit code for grading against all test cases (visible + hidden).

    Creates a Submission record (is_full_submit=True), enqueues it for
    execution in the Celery worker, and returns the submission_id immediately.
    Tags with active lab session if applicable.
    """
    problem = await _get_problem_or_404(slug, db)

    lab_session_id = body.lab_session_id
    if lab_session_id is None:
        # Check if there is an active lab session for this problem
        active_lab_q = (
            select(LabSession.id)
            .join(LabSessionProblem, LabSessionProblem.lab_session_id == LabSession.id)
            .where(
                LabSessionProblem.problem_id == problem.id,
                LabSession.is_active.is_(True),
            )
            .order_by(LabSession.created_at.desc())
        )
        active_res = await db.execute(active_lab_q)
        lab_session_id = active_res.scalars().first()

    submission = Submission(
        id=uuid.uuid4(),
        problem_id=problem.id,
        user_id=current_user.id,
        lab_session_id=lab_session_id,
        language=body.language,
        source_code=body.source_code,
        status="queued",
        is_full_submit=True,
    )
    db.add(submission)
    await db.flush()

    submission_id = str(submission.id)
    await db.commit()

    grade_submission.delay(submission_id)
    return SubmissionCreated(submission_id=submission_id)


# ── GET /problems/{id_or_slug}/submissions ────────────────────────────────────

@router.get("/{id_or_slug}/submissions", response_model=list[SubmissionSummaryResponse])
async def get_submission_history(
    id_or_slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SubmissionSummaryResponse]:
    """Return submission history for the authenticated user on this problem.

    Ordered by `submitted_at DESC`. The best submission (highest score, earliest if tied)
    is marked with `is_best=True`. Accepts either problem UUID or slug.
    """
    try:
        p_uuid = uuid.UUID(id_or_slug)
        stmt = select(Problem).where(Problem.id == p_uuid)
    except ValueError:
        stmt = select(Problem).where(Problem.slug == id_or_slug)

    result = await db.execute(stmt)
    problem = result.scalar_one_or_none()
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{id_or_slug}' not found.",
        )

    subs_res = await db.execute(
        select(Submission)
        .where(
            Submission.problem_id == problem.id,
            Submission.user_id == current_user.id,
        )
        .order_by(Submission.submitted_at.desc())
    )
    submissions = list(subs_res.scalars().all())

    # Best submission: highest score, earliest submitted_at if tied
    best_id: uuid.UUID | None = None
    scored = [s for s in submissions if s.score is not None and s.is_full_submit]
    if not scored:
        scored = [s for s in submissions if s.score is not None]

    if scored:
        best_sub = min(scored, key=lambda s: (-s.score, s.submitted_at))
        best_id = best_sub.id

    out: list[SubmissionSummaryResponse] = []
    for s in submissions:
        item = SubmissionSummaryResponse.model_validate(s)
        item.is_best = (s.id == best_id)
        out.append(item)

    return out


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

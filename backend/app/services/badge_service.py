"""Badge evaluation service for lab sessions.

Badge awarding rules:
- Only awarded for full submissions (is_full_submit=True) during an active lab session.
- Only awarded if submission score is 100 (all test cases passed).
- Count distinct problems the student has solved in this lab session.
- If distinct solved count > lab.mandatory_count:
    Award a badge for the newly solved problem (if not already awarded).
- Each badge is an individual row in the `badges` table (one badge per extra problem solved).
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.badge import Badge
from app.models.lab_session import LabSession, LabSessionProblem
from app.models.submission import Submission

logger = logging.getLogger(__name__)


def evaluate_badges_sync(session: Session, submission: Submission) -> Badge | None:
    """Synchronous badge evaluation hook (for Celery worker)."""
    if not submission.lab_session_id or not submission.is_full_submit:
        return None
    if submission.score != 100:
        return None

    lab = session.get(LabSession, submission.lab_session_id)
    if not lab or not lab.is_active:
        return None

    # Verify problem belongs to this lab session
    lab_prob = session.execute(
        select(LabSessionProblem).where(
            LabSessionProblem.lab_session_id == lab.id,
            LabSessionProblem.problem_id == submission.problem_id,
        )
    ).scalar_one_or_none()
    if not lab_prob:
        return None

    # Count distinct problems solved by this student in this lab
    solved_problem_ids = session.execute(
        select(Submission.problem_id)
        .where(
            Submission.user_id == submission.user_id,
            Submission.lab_session_id == lab.id,
            Submission.is_full_submit.is_(True),
            Submission.score == 100,
        )
        .distinct()
    ).scalars().all()

    distinct_count = len(solved_problem_ids)
    if distinct_count <= lab.mandatory_count:
        return None

    # Check if a badge is already awarded for this problem
    existing_badge = session.execute(
        select(Badge).where(
            Badge.user_id == submission.user_id,
            Badge.lab_session_id == lab.id,
            Badge.problem_id == submission.problem_id,
        )
    ).scalar_one_or_none()

    if existing_badge is not None:
        return None

    # Award badge
    badge = Badge(
        id=uuid.uuid4(),
        user_id=submission.user_id,
        lab_session_id=lab.id,
        problem_id=submission.problem_id,
    )
    session.add(badge)
    session.commit()
    logger.info(
        "Awarded badge %s to user %s for problem %s in lab %s",
        badge.id,
        submission.user_id,
        submission.problem_id,
        lab.id,
    )
    return badge


async def evaluate_badges_async(db: AsyncSession, submission: Submission) -> Badge | None:
    """Asynchronous badge evaluation hook (for FastAPI routes / direct calls)."""
    if not submission.lab_session_id or not submission.is_full_submit:
        return None
    if submission.score != 100:
        return None

    result = await db.execute(
        select(LabSession).where(LabSession.id == submission.lab_session_id)
    )
    lab = result.scalar_one_or_none()
    if not lab or not lab.is_active:
        return None

    # Verify problem belongs to this lab session
    lp_res = await db.execute(
        select(LabSessionProblem).where(
            LabSessionProblem.lab_session_id == lab.id,
            LabSessionProblem.problem_id == submission.problem_id,
        )
    )
    if lp_res.scalar_one_or_none() is None:
        return None

    # Count distinct problems solved by this student in this lab
    solved_res = await db.execute(
        select(Submission.problem_id)
        .where(
            Submission.user_id == submission.user_id,
            Submission.lab_session_id == lab.id,
            Submission.is_full_submit.is_(True),
            Submission.score == 100,
        )
        .distinct()
    )
    solved_problem_ids = solved_res.scalars().all()

    distinct_count = len(solved_problem_ids)
    if distinct_count <= lab.mandatory_count:
        return None

    # Check if a badge is already awarded for this problem
    badge_res = await db.execute(
        select(Badge).where(
            Badge.user_id == submission.user_id,
            Badge.lab_session_id == lab.id,
            Badge.problem_id == submission.problem_id,
        )
    )
    if badge_res.scalar_one_or_none() is not None:
        return None

    badge = Badge(
        id=uuid.uuid4(),
        user_id=submission.user_id,
        lab_session_id=lab.id,
        problem_id=submission.problem_id,
    )
    db.add(badge)
    await db.commit()
    logger.info(
        "Awarded badge %s to user %s for problem %s in lab %s",
        badge.id,
        submission.user_id,
        submission.problem_id,
        lab.id,
    )
    return badge

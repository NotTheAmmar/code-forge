"""FastAPI router for Lab Sessions and Badge tracking.

Routes:
    POST /courses/{course_id}/labs   → create lab session (instructor only)
    GET  /courses/{course_id}/labs   → list labs in course (enrolled users)
    GET  /labs/{lab_id}              → lab details + problems (enrolled users)
    PUT  /labs/{lab_id}              → update lab session (instructor only)
    GET  /labs/{lab_id}/dashboard    → real-time dashboard with badges & solves (instructor only)
    GET  /labs/{lab_id}/my-progress  → student progress & badges (enrolled users)
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.dependencies import get_current_user
from app.models.badge import Badge
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lab_session import LabSession, LabSessionProblem
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.schemas.lab import (
    LabDashboardResponse,
    LabDashboardStudent,
    LabProblemItem,
    LabSessionCreate,
    LabSessionDetailResponse,
    LabSessionResponse,
    LabSessionUpdate,
    StudentLabProgressResponse,
)

router = APIRouter(tags=["labs"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_enrollment_or_403(
    course_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Enrollment:
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user_id,
        )
    )
    enr = result.scalar_one_or_none()
    if enr is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this course.",
        )
    return enr


async def _get_lab_or_404(lab_id: uuid.UUID, db: AsyncSession) -> LabSession:
    result = await db.execute(
        select(LabSession)
        .where(LabSession.id == lab_id)
        .options(
            selectinload(LabSession.lab_problems).selectinload(LabSessionProblem.problem)
        )
    )
    lab = result.scalar_one_or_none()
    if lab is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab session not found.",
        )
    return lab


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/courses/{course_id}/labs",
    response_model=LabSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a lab session (instructor only)",
)
async def create_lab_session(
    course_id: uuid.UUID,
    body: LabSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabSessionResponse:
    """Create a lab session in the course and attach assigned problems."""
    enrollment = await _get_enrollment_or_403(course_id, current_user.id, db)
    if enrollment.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course instructors can create lab sessions.",
        )

    # Validate problem IDs if provided
    if body.problem_ids:
        prob_res = await db.execute(
            select(Problem.id).where(
                Problem.id.in_(body.problem_ids),
                Problem.course_id == course_id,
            )
        )
        existing_prob_ids = set(prob_res.scalars().all())
        missing = [pid for pid in body.problem_ids if pid not in existing_prob_ids]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Some problems were not found in this course: {missing}",
            )

    lab = LabSession(
        id=uuid.uuid4(),
        course_id=course_id,
        title=body.title,
        description=body.description,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        mandatory_count=body.mandatory_count,
        is_active=True,
    )
    db.add(lab)
    await db.flush()

    for idx, pid in enumerate(body.problem_ids):
        db.add(
            LabSessionProblem(
                id=uuid.uuid4(),
                lab_session_id=lab.id,
                problem_id=pid,
                order_index=idx,
            )
        )

    await db.commit()
    await db.refresh(lab)

    return LabSessionResponse(
        id=lab.id,
        course_id=lab.course_id,
        title=lab.title,
        description=lab.description,
        starts_at=lab.starts_at,
        ends_at=lab.ends_at,
        mandatory_count=lab.mandatory_count,
        problem_count=len(body.problem_ids),
        is_active=lab.is_active,
        created_at=lab.created_at,
    )


@router.get(
    "/courses/{course_id}/labs",
    response_model=list[LabSessionResponse],
    summary="List lab sessions for a course (enrolled users)",
)
async def list_course_labs(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LabSessionResponse]:
    """Return all lab sessions for a course."""
    await _get_enrollment_or_403(course_id, current_user.id, db)

    result = await db.execute(
        select(LabSession)
        .where(LabSession.course_id == course_id)
        .order_by(LabSession.created_at.desc())
    )
    labs = result.scalars().all()
    if not labs:
        return []

    lab_ids = [l.id for l in labs]
    counts_res = await db.execute(
        select(LabSessionProblem.lab_session_id, func.count(LabSessionProblem.id))
        .where(LabSessionProblem.lab_session_id.in_(lab_ids))
        .group_by(LabSessionProblem.lab_session_id)
    )
    prob_counts = dict(counts_res.all())

    return [
        LabSessionResponse(
            id=l.id,
            course_id=l.course_id,
            title=l.title,
            description=l.description,
            starts_at=l.starts_at,
            ends_at=l.ends_at,
            mandatory_count=l.mandatory_count,
            problem_count=prob_counts.get(l.id, 0),
            is_active=l.is_active,
            created_at=l.created_at,
        )
        for l in labs
    ]


@router.get(
    "/labs/{lab_id}",
    response_model=LabSessionDetailResponse,
    summary="Get lab session detail and assigned problems (enrolled users)",
)
async def get_lab_detail(
    lab_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabSessionDetailResponse:
    """Return lab details and the ordered list of problems assigned to it."""
    lab = await _get_lab_or_404(lab_id, db)
    await _get_enrollment_or_403(lab.course_id, current_user.id, db)

    problems = [
        LabProblemItem(
            id=lp.problem.id,
            slug=lp.problem.slug,
            title=lp.problem.title,
            difficulty=lp.problem.difficulty,
            order_index=lp.order_index,
        )
        for lp in lab.lab_problems
        if lp.problem is not None
    ]

    return LabSessionDetailResponse(
        id=lab.id,
        course_id=lab.course_id,
        title=lab.title,
        description=lab.description,
        starts_at=lab.starts_at,
        ends_at=lab.ends_at,
        mandatory_count=lab.mandatory_count,
        is_active=lab.is_active,
        problems=problems,
        created_at=lab.created_at,
    )


@router.put(
    "/labs/{lab_id}",
    response_model=LabSessionDetailResponse,
    summary="Update a lab session (instructor only)",
)
async def update_lab_session(
    lab_id: uuid.UUID,
    body: LabSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabSessionDetailResponse:
    """Update lab session fields and optionally replace assigned problems."""
    lab = await _get_lab_or_404(lab_id, db)
    enrollment = await _get_enrollment_or_403(lab.course_id, current_user.id, db)
    if enrollment.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course instructors can update lab sessions.",
        )

    for field in ("title", "description", "starts_at", "ends_at", "mandatory_count", "is_active"):
        val = getattr(body, field)
        if val is not None:
            setattr(lab, field, val)

    if body.problem_ids is not None:
        # Validate problems belong to course
        if body.problem_ids:
            prob_res = await db.execute(
                select(Problem.id).where(
                    Problem.id.in_(body.problem_ids),
                    Problem.course_id == lab.course_id,
                )
            )
            existing_ids = set(prob_res.scalars().all())
            missing = [pid for pid in body.problem_ids if pid not in existing_ids]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Some problems were not found in this course: {missing}",
                )

        lab.lab_problems.clear()
        for idx, pid in enumerate(body.problem_ids):
            lab.lab_problems.append(
                LabSessionProblem(
                    id=uuid.uuid4(),
                    lab_session_id=lab.id,
                    problem_id=pid,
                    order_index=idx,
                )
            )

    await db.commit()
    # Reload fresh
    return await get_lab_detail(lab_id, current_user, db)


@router.get(
    "/labs/{lab_id}/dashboard",
    response_model=LabDashboardResponse,
    summary="Real-time lab session dashboard (instructor only)",
)
async def get_lab_dashboard(
    lab_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabDashboardResponse:
    """Aggregate per-student progress, problems solved, and badges earned."""
    lab = await _get_lab_or_404(lab_id, db)
    enrollment = await _get_enrollment_or_403(lab.course_id, current_user.id, db)
    if enrollment.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course instructors can view the lab dashboard.",
        )

    # Get all students enrolled in the course
    enrolled_res = await db.execute(
        select(Enrollment)
        .where(
            Enrollment.course_id == lab.course_id,
            Enrollment.role == "student",
        )
        .options(selectinload(Enrollment.user))
        .order_by(Enrollment.joined_at)
    )
    student_enrollments = enrolled_res.scalars().all()
    student_users = [e.user for e in student_enrollments]

    student_rows: list[LabDashboardStudent] = []
    total_badges = 0
    active_count = 0

    if student_users:
        student_ids = [u.id for u in student_users]

        # Solved problems per student in this lab session
        solved_res = await db.execute(
            select(Submission.user_id, Submission.problem_id)
            .where(
                Submission.lab_session_id == lab.id,
                Submission.user_id.in_(student_ids),
                Submission.is_full_submit.is_(True),
                Submission.score == 100,
            )
            .distinct()
        )
        student_solves: dict[uuid.UUID, set[uuid.UUID]] = {}
        for uid, pid in solved_res.all():
            student_solves.setdefault(uid, set()).add(pid)

        # Badge count per student in this lab session
        badge_res = await db.execute(
            select(Badge.user_id, func.count(Badge.id))
            .where(
                Badge.lab_session_id == lab.id,
                Badge.user_id.in_(student_ids),
            )
            .group_by(Badge.user_id)
        )
        student_badges = dict(badge_res.all())

        # Last submission time per student in this lab session
        last_sub_res = await db.execute(
            select(Submission.user_id, func.max(Submission.submitted_at))
            .where(
                Submission.lab_session_id == lab.id,
                Submission.user_id.in_(student_ids),
            )
            .group_by(Submission.user_id)
        )
        last_subs = dict(last_sub_res.all())

        for u in student_users:
            solved_set = student_solves.get(u.id, set())
            solved_count = len(solved_set)
            badges = student_badges.get(u.id, 0)
            last_sub = last_subs.get(u.id)

            if last_sub is not None:
                active_count += 1
            total_badges += badges

            student_rows.append(
                LabDashboardStudent(
                    user_id=u.id,
                    name=u.name,
                    email=u.email,
                    problems_solved=solved_count,
                    mandatory_completed=solved_count >= lab.mandatory_count,
                    badge_count=badges,
                    last_submission_at=last_sub,
                )
            )

    # Sort students by badge_count desc, problems_solved desc, name asc
    student_rows.sort(
        key=lambda s: (-s.badge_count, -s.problems_solved, s.name.lower())
    )

    return LabDashboardResponse(
        lab_id=lab.id,
        title=lab.title,
        mandatory_count=lab.mandatory_count,
        total_students=len(student_users),
        active_students=active_count,
        total_badges_awarded=total_badges,
        students=student_rows,
    )


@router.get(
    "/labs/{lab_id}/my-progress",
    response_model=StudentLabProgressResponse,
    summary="Get current student's lab progress and badges (enrolled users)",
)
async def get_my_lab_progress(
    lab_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentLabProgressResponse:
    """Return problems solved, mandatory status, and earned badges for the current student."""
    lab = await _get_lab_or_404(lab_id, db)
    await _get_enrollment_or_403(lab.course_id, current_user.id, db)

    # Problems solved in this lab
    solved_res = await db.execute(
        select(Submission.problem_id)
        .where(
            Submission.lab_session_id == lab.id,
            Submission.user_id == current_user.id,
            Submission.is_full_submit.is_(True),
            Submission.score == 100,
        )
        .distinct()
    )
    solved_ids = list(solved_res.scalars().all())
    solved_count = len(solved_ids)

    # Badges earned in this lab
    badge_res = await db.execute(
        select(Badge)
        .where(
            Badge.lab_session_id == lab.id,
            Badge.user_id == current_user.id,
        )
        .order_by(Badge.earned_at.desc())
    )
    badges = badge_res.scalars().all()
    badge_count = len(badges)

    recent_badge: dict[str, Any] | None = None
    if badges:
        most_recent = badges[0]
        recent_badge = {
            "problem_id": str(most_recent.problem_id),
            "earned_at": most_recent.earned_at.isoformat(),
        }

    return StudentLabProgressResponse(
        lab_id=lab.id,
        mandatory_count=lab.mandatory_count,
        problems_solved_count=solved_count,
        mandatory_completed=solved_count >= lab.mandatory_count,
        badge_count=badge_count,
        solved_problem_ids=solved_ids,
        recent_badge_earned=recent_badge,
    )

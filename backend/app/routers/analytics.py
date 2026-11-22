"""FastAPI router for Performance Analytics, Error Distributions, and Student Tracking.

Endpoints:
    GET /courses/{course_id}/analytics                 → course overview stats (instructor)
    GET /courses/{course_id}/analytics/students/{uid}   → student progress breakdown (instructor or self)
    GET /problems/{id_or_slug}/analytics              → per-problem performance stats (instructor)
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.dependencies import get_current_user
from app.models.badge import Badge
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.schemas.analytics import (
    CourseAnalyticsResponse,
    ErrorDistributionItem,
    ProblemAnalyticsResponse,
    ProblemPassRate,
    ScoreProgressionItem,
    StudentAnalyticsResponse,
    SubmissionTrendItem,
    SummaryStats,
)

router = APIRouter(tags=["analytics"])


# ── Permission Helpers ────────────────────────────────────────────────────────

async def _get_course_or_404(course_id: uuid.UUID, db: AsyncSession) -> Course:
    res = await db.execute(select(Course).where(Course.id == course_id))
    course = res.scalar_one_or_none()
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_id}' not found.",
        )
    return course


def _ensure_course_instructor(course: Course, current_user: User) -> None:
    if current_user.role != "instructor" or course.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor access required for this course analytics.",
        )


async def _resolve_problem_or_404(id_or_slug: str, db: AsyncSession) -> Problem:
    try:
        prob_uuid = uuid.UUID(id_or_slug)
        res = await db.execute(
            select(Problem).where(Problem.id == prob_uuid).options(selectinload(Problem.course))
        )
    except ValueError:
        res = await db.execute(
            select(Problem).where(Problem.slug == id_or_slug).options(selectinload(Problem.course))
        )
    prob = res.scalar_one_or_none()
    if prob is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{id_or_slug}' not found.",
        )
    return prob


# ── Course-Wide Analytics ─────────────────────────────────────────────────────

@router.get(
    "/courses/{course_id}/analytics",
    response_model=CourseAnalyticsResponse,
)
async def get_course_analytics(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseAnalyticsResponse:
    """Course-wide analytics: pass rates, error distributions, and submission trends (Instructor only)."""
    course = await _get_course_or_404(course_id, db)
    _ensure_course_instructor(course, current_user)

    # 1. Total students
    enr_count_res = await db.execute(
        select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id)
    )
    total_students = enr_count_res.scalar() or 0

    # 2. Problems in course
    prob_res = await db.execute(select(Problem).where(Problem.course_id == course_id))
    problems = prob_res.scalars().all()
    problem_ids = [p.id for p in problems]

    if not problem_ids:
        return CourseAnalyticsResponse(
            course_id=course_id,
            summary=SummaryStats(
                total_students=total_students,
                total_submissions=0,
                average_pass_rate=0.0,
                active_students_7d=0,
            ),
            problem_pass_rates=[],
            common_error_distribution=[],
            submission_trends=[],
        )

    # 3. Submissions for course problems
    subs_res = await db.execute(
        select(Submission).where(Submission.problem_id.in_(problem_ids))
    )
    submissions = subs_res.scalars().all()
    total_submissions = len(submissions)

    # 4. Accepted count & average pass rate
    accepted_subs = [s for s in submissions if s.status == "accepted"]
    avg_pass_rate = (
        round((len(accepted_subs) / total_submissions) * 100, 1)
        if total_submissions > 0
        else 0.0
    )

    # 5. Active students in last 7 days
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    def _to_utc(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    active_7d_users = {
        s.user_id
        for s in submissions
        if s.submitted_at and (_to_utc(s.submitted_at) or now) >= seven_days_ago
    }

    summary = SummaryStats(
        total_students=total_students,
        total_submissions=total_submissions,
        average_pass_rate=avg_pass_rate,
        active_students_7d=len(active_7d_users),
    )

    # 6. Problem pass rates
    problem_pass_rates = []
    for p in problems:
        p_subs = [s for s in submissions if s.problem_id == p.id]
        p_count = len(p_subs)
        p_accepted = sum(1 for s in p_subs if s.status == "accepted")
        p_pass_rate = round((p_accepted / p_count) * 100, 1) if p_count > 0 else 0.0
        scores = [s.score for s in p_subs if s.score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        problem_pass_rates.append(
            ProblemPassRate(
                problem_id=p.id,
                title=p.title,
                difficulty=p.difficulty,
                submissions_count=p_count,
                pass_rate=p_pass_rate,
                average_score=avg_score,
            )
        )

    # 7. Common error distribution
    error_counts: dict[str, int] = {
        "compile_error": 0,
        "timeout": 0,
        "runtime_error": 0,
        "wrong_answer": 0,
    }
    for s in submissions:
        if s.status in error_counts:
            error_counts[s.status] += 1
        elif s.status != "accepted":
            error_counts[s.status] = error_counts.get(s.status, 0) + 1

    common_error_distribution = [
        ErrorDistributionItem(error_type=k, count=v) for k, v in error_counts.items()
    ]

    # 8. Submission trends over last 7 days
    date_counts: dict[str, int] = {}
    for i in range(6, -1, -1):
        day_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        date_counts[day_str] = 0

    for s in submissions:
        if s.submitted_at:
            d_str = s.submitted_at.strftime("%Y-%m-%d")
            if d_str in date_counts:
                date_counts[d_str] += 1

    submission_trends = [
        SubmissionTrendItem(date=d, count=c) for d, c in date_counts.items()
    ]

    return CourseAnalyticsResponse(
        course_id=course_id,
        summary=summary,
        problem_pass_rates=problem_pass_rates,
        common_error_distribution=common_error_distribution,
        submission_trends=submission_trends,
    )


# ── Student Analytics ─────────────────────────────────────────────────────────

@router.get(
    "/courses/{course_id}/analytics/students/{user_id}",
    response_model=StudentAnalyticsResponse,
)
async def get_student_analytics(
    course_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentAnalyticsResponse:
    """Individual student performance analytics (Student self or Course Instructor)."""
    course = await _get_course_or_404(course_id, db)

    # Access check: Instructor of course or self
    is_instructor = (current_user.role == "instructor" and course.created_by == current_user.id)
    if not is_instructor and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access analytics of another student.",
        )

    # Fetch target user
    user_res = await db.execute(select(User).where(User.id == user_id))
    target_user = user_res.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    # Problems in course
    prob_res = await db.execute(select(Problem).where(Problem.course_id == course_id))
    problems = {p.id: p for p in prob_res.scalars().all()}
    problem_ids = list(problems.keys())

    # Submissions of this student in course
    subs_res = await db.execute(
        select(Submission)
        .where(
            Submission.user_id == user_id,
            Submission.problem_id.in_(problem_ids),
        )
        .order_by(Submission.submitted_at.asc())
    )
    submissions = subs_res.scalars().all()
    total_subs = len(submissions)

    solved_prob_ids = {s.problem_id for s in submissions if s.status == "accepted"}

    # Badges earned
    badge_res = await db.execute(select(func.count(Badge.id)).where(Badge.user_id == user_id))
    badges_earned = badge_res.scalar() or 0

    # Score progression
    score_progression = [
        ScoreProgressionItem(
            submitted_at=s.submitted_at,
            problem=problems[s.problem_id].title if s.problem_id in problems else "Unknown",
            score=s.score or 0,
        )
        for s in submissions
        if s.submitted_at is not None
    ]

    return StudentAnalyticsResponse(
        user_id=user_id,
        name=target_user.name,
        total_submissions=total_subs,
        problems_solved=len(solved_prob_ids),
        badges_earned=badges_earned,
        score_progression=score_progression,
    )


# ── Problem Analytics ─────────────────────────────────────────────────────────

@router.get(
    "/problems/{id_or_slug}/analytics",
    response_model=ProblemAnalyticsResponse,
)
async def get_problem_analytics(
    id_or_slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProblemAnalyticsResponse:
    """Problem-level submission analytics and language breakdown (Course Instructor)."""
    problem = await _resolve_problem_or_404(id_or_slug, db)
    if problem.course_id:
        course = await _get_course_or_404(problem.course_id, db)
        _ensure_course_instructor(course, current_user)
    elif current_user.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor access required for problem analytics.",
        )

    subs_res = await db.execute(
        select(Submission).where(Submission.problem_id == problem.id)
    )
    submissions = subs_res.scalars().all()
    total_submissions = len(submissions)

    unique_students = len({s.user_id for s in submissions})
    accepted_count = sum(1 for s in submissions if s.status == "accepted")
    pass_rate = round((accepted_count / total_submissions) * 100, 1) if total_submissions > 0 else 0.0

    lang_counts: dict[str, int] = {"python": 0, "java": 0, "c": 0, "cpp": 0}
    exec_times: list[int] = []

    for s in submissions:
        l = (s.language or "python").strip().lower()
        lang_counts[l] = lang_counts.get(l, 0) + 1
        if s.execution_time_ms is not None:
            exec_times.append(s.execution_time_ms)

    avg_exec_time = round(sum(exec_times) / len(exec_times)) if exec_times else 0

    return ProblemAnalyticsResponse(
        problem_id=problem.id,
        slug=problem.slug,
        title=problem.title,
        total_submissions=total_submissions,
        unique_students=unique_students,
        pass_rate=pass_rate,
        language_breakdown=lang_counts,
        average_execution_time_ms=avg_exec_time,
    )

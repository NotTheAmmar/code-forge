"""FastAPI router for Proctored Assessment, Lockdown Sessions, and Anti-Cheat Monitoring.

Endpoints:
    POST   /courses/{course_id}/exams              → create proctored exam (instructor)
    GET    /courses/{course_id}/exams              → list exams with session status (enrolled)
    GET    /exams/{exam_id}                        → get exam detail (enrolled)
    PUT    /exams/{exam_id}                        → update exam config (instructor)
    DELETE /exams/{exam_id}                        → delete exam (instructor)

    POST   /exams/{exam_id}/start                  → start lockdown session (student)
    POST   /exam-sessions/{session_id}/violations  → log browser / focus violation (student)
    POST   /exams/{exam_id}/submit                 → submit exam session (student)
    GET    /exams/{exam_id}/results                → instructor results & integrity dashboard
    GET    /exams/{exam_id}/my-result              → student's own exam results
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.dependencies import get_current_user
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.exam import Exam, ExamProblem
from app.models.exam_session import ExamSession
from app.models.exam_violation import ExamViolation
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.schemas.exam import (
    ExamCreate,
    ExamDetailResponse,
    ExamMyResultResponse,
    ExamProblemResponse,
    ExamResponse,
    ExamResultsDashboard,
    ExamSessionStartResponse,
    ExamSessionSummary,
    ExamStudentResult,
    ExamSubmitRequest,
    ExamUpdate,
    ExamViolationCreate,
    ExamViolationResponse,
)

router = APIRouter(tags=["exams"])


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


async def _get_exam_or_404(exam_id: uuid.UUID, db: AsyncSession) -> Exam:
    res = await db.execute(
        select(Exam)
        .where(Exam.id == exam_id)
        .options(
            selectinload(Exam.problems).selectinload(ExamProblem.problem),
            selectinload(Exam.course),
        )
    )
    exam = res.scalar_one_or_none()
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam '{exam_id}' not found.",
        )
    return exam


async def _get_session_or_404(session_id: uuid.UUID, db: AsyncSession) -> ExamSession:
    res = await db.execute(
        select(ExamSession)
        .where(ExamSession.id == session_id)
        .options(
            selectinload(ExamSession.exam),
            selectinload(ExamSession.violations),
        )
    )
    session = res.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam session '{session_id}' not found.",
        )
    return session


async def _ensure_course_access(course: Course, current_user: User, db: AsyncSession) -> None:
    if course.created_by == current_user.id:
        return
    enr_res = await db.execute(
        select(Enrollment).where(
            Enrollment.course_id == course.id,
            Enrollment.user_id == current_user.id,
        )
    )
    if enr_res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this course.",
        )


def _ensure_course_instructor(course: Course, current_user: User) -> None:
    if current_user.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor access required for this course.",
        )
    if course.created_by != current_user.id and current_user.email != "admin@codeforge.local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor access required for this course.",
        )


def _to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _build_exam_problem_response(ep: ExamProblem, conceal: bool = False) -> ExamProblemResponse:
    p = ep.problem
    return ExamProblemResponse(
        id=ep.problem_id,
        slug=p.slug if not conceal else "",
        title=p.title if not conceal else f"Problem {ep.order_index}",
        difficulty=p.difficulty if not conceal else "medium",
        weight=ep.weight,
        order_index=ep.order_index,
        description=p.description if not conceal else "Concealed until exam session begins.",
        starter_code_python=p.starter_code_python if not conceal else None,
        starter_code_java=p.starter_code_java if not conceal else None,
        starter_code_c=p.starter_code_c if not conceal else None,
        starter_code_cpp=p.starter_code_cpp if not conceal else None,
    )


# ── Exam Endpoints ────────────────────────────────────────────────────────────

@router.post(
    "/courses/{course_id}/exams",
    response_model=ExamDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exam(
    course_id: uuid.UUID,
    body: ExamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamDetailResponse:
    """Create a new proctored exam with anti-cheat configuration (Instructor only)."""
    course = await _get_course_or_404(course_id, db)
    _ensure_course_instructor(course, current_user)

    starts_at = _to_utc(body.starts_at)
    ends_at = _to_utc(body.ends_at)
    if ends_at <= starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam ends_at must be strictly after starts_at.",
        )

    exam = Exam(
        id=uuid.uuid4(),
        course_id=course_id,
        title=body.title,
        description=body.description,
        duration_minutes=body.duration_minutes,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        is_active=body.is_active,
        fullscreen_required=body.fullscreen_required,
        tab_switch_limit=body.tab_switch_limit,
        copy_paste_blocked=body.copy_paste_blocked,
        created_by=current_user.id,
    )
    db.add(exam)
    await db.flush()

    exam_problems = []
    for item in body.problems:
        prob_res = await db.execute(select(Problem).where(Problem.id == item.problem_id))
        prob = prob_res.scalar_one_or_none()
        if prob is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Problem '{item.problem_id}' not found.",
            )
        ep = ExamProblem(
            id=uuid.uuid4(),
            exam_id=exam.id,
            problem_id=item.problem_id,
            order_index=item.order_index,
            weight=item.weight,
        )
        db.add(ep)
        exam_problems.append((ep, prob))

    await db.commit()

    problems_resp = [
        ExamProblemResponse(
            id=prob.id,
            slug=prob.slug,
            title=prob.title,
            difficulty=prob.difficulty,
            weight=ep.weight,
            order_index=ep.order_index,
            description=prob.description,
            starter_code_python=prob.starter_code_python,
            starter_code_java=prob.starter_code_java,
            starter_code_c=prob.starter_code_c,
            starter_code_cpp=prob.starter_code_cpp,
        )
        for ep, prob in exam_problems
    ]

    return ExamDetailResponse(
        id=exam.id,
        course_id=exam.course_id,
        title=exam.title,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        starts_at=exam.starts_at,
        ends_at=exam.ends_at,
        is_active=exam.is_active,
        fullscreen_required=exam.fullscreen_required,
        tab_switch_limit=exam.tab_switch_limit,
        copy_paste_blocked=exam.copy_paste_blocked,
        problem_count=len(exam_problems),
        has_session=False,
        session_status=None,
        created_at=exam.created_at,
        problems=problems_resp,
    )


@router.get(
    "/courses/{course_id}/exams",
    response_model=list[ExamResponse],
)
async def list_course_exams(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ExamResponse]:
    """List exams for a course with per-student sitting status."""
    course = await _get_course_or_404(course_id, db)
    await _ensure_course_access(course, current_user, db)

    res = await db.execute(
        select(Exam)
        .where(Exam.course_id == course_id)
        .options(selectinload(Exam.problems))
        .order_by(Exam.starts_at.desc())
    )
    exams = res.scalars().all()

    # Fetch user sessions
    sess_res = await db.execute(
        select(ExamSession).where(
            ExamSession.user_id == current_user.id,
            ExamSession.exam_id.in_([e.id for e in exams]),
        )
    )
    user_sessions = {s.exam_id: s for s in sess_res.scalars().all()}

    output = []
    for e in exams:
        sess = user_sessions.get(e.id)
        has_session = sess is not None
        session_status = None
        if sess is not None:
            session_status = "submitted" if sess.submitted_at else "in_progress"

        output.append(
            ExamResponse(
                id=e.id,
                course_id=e.course_id,
                title=e.title,
                description=e.description,
                duration_minutes=e.duration_minutes,
                starts_at=e.starts_at,
                ends_at=e.ends_at,
                is_active=e.is_active,
                fullscreen_required=e.fullscreen_required,
                tab_switch_limit=e.tab_switch_limit,
                copy_paste_blocked=e.copy_paste_blocked,
                problem_count=len(e.problems),
                has_session=has_session,
                session_status=session_status,
                created_at=e.created_at,
            )
        )
    return output


@router.get(
    "/exams/{exam_id}",
    response_model=ExamDetailResponse,
)
async def get_exam_detail(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamDetailResponse:
    """Get exam details. For students, problem contents are concealed before starting session."""
    exam = await _get_exam_or_404(exam_id, db)
    await _ensure_course_access(exam.course, current_user, db)

    is_instructor = (exam.course.created_by == current_user.id)

    sess_res = await db.execute(
        select(ExamSession).where(
            ExamSession.exam_id == exam.id,
            ExamSession.user_id == current_user.id,
        )
    )
    sess = sess_res.scalar_one_or_none()
    has_session = sess is not None
    session_status = "submitted" if sess and sess.submitted_at else ("in_progress" if sess else None)

    # Conceal problem content for students who haven't started session yet
    conceal = not is_instructor and not has_session

    sorted_problems = sorted(exam.problems, key=lambda p: p.order_index)
    problems_resp = [_build_exam_problem_response(ep, conceal=conceal) for ep in sorted_problems]

    return ExamDetailResponse(
        id=exam.id,
        course_id=exam.course_id,
        title=exam.title,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        starts_at=exam.starts_at,
        ends_at=exam.ends_at,
        is_active=exam.is_active,
        fullscreen_required=exam.fullscreen_required,
        tab_switch_limit=exam.tab_switch_limit,
        copy_paste_blocked=exam.copy_paste_blocked,
        problem_count=len(sorted_problems),
        has_session=has_session,
        session_status=session_status,
        created_at=exam.created_at,
        problems=problems_resp,
    )


@router.put(
    "/exams/{exam_id}",
    response_model=ExamDetailResponse,
)
async def update_exam(
    exam_id: uuid.UUID,
    body: ExamUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamDetailResponse:
    """Update exam configuration (Instructor only)."""
    exam = await _get_exam_or_404(exam_id, db)
    _ensure_course_instructor(exam.course, current_user)

    if body.title is not None:
        exam.title = body.title
    if body.description is not None:
        exam.description = body.description
    if body.duration_minutes is not None:
        exam.duration_minutes = body.duration_minutes
    if body.starts_at is not None:
        exam.starts_at = body.starts_at
    if body.ends_at is not None:
        exam.ends_at = body.ends_at
    if body.is_active is not None:
        exam.is_active = body.is_active
    if body.fullscreen_required is not None:
        exam.fullscreen_required = body.fullscreen_required
    if body.tab_switch_limit is not None:
        exam.tab_switch_limit = body.tab_switch_limit
    if body.copy_paste_blocked is not None:
        exam.copy_paste_blocked = body.copy_paste_blocked

    if body.problems is not None:
        # Replace problems
        await db.execute(select(ExamProblem).where(ExamProblem.exam_id == exam.id))
        for ep in list(exam.problems):
            await db.delete(ep)
        for item in body.problems:
            db.add(
                ExamProblem(
                    id=uuid.uuid4(),
                    exam_id=exam.id,
                    problem_id=item.problem_id,
                    order_index=item.order_index,
                    weight=item.weight,
                )
            )

    await db.commit()
    return await get_exam_detail(exam.id, current_user, db)


@router.delete(
    "/exams/{exam_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an exam and all related sessions (Instructor only)."""
    exam = await _get_exam_or_404(exam_id, db)
    _ensure_course_instructor(exam.course, current_user)

    await db.delete(exam)
    await db.commit()


# ── Exam Lockdown & Session Endpoints ─────────────────────────────────────────

@router.post(
    "/exams/{exam_id}/start",
    response_model=ExamSessionStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_exam_session(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamSessionStartResponse:
    """Start exam session and enter lockdown. Enforces time window & single session guarantee."""
    exam = await _get_exam_or_404(exam_id, db)
    await _ensure_course_access(exam.course, current_user, db)

    # Instructors must not take exams as examinees
    if current_user.role == "instructor" or exam.course.created_by == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructors cannot take exams. Review submissions in the Exam Results & Integrity Dashboard.",
        )

    if not exam.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This exam is currently not active.",
        )

    now = datetime.now(timezone.utc)
    starts_at = _to_utc(exam.starts_at)
    ends_at = _to_utc(exam.ends_at)
    if starts_at and now < starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exam window has not opened yet. Starts at {starts_at.isoformat()}.",
        )
    if ends_at and now > ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exam window has closed at {ends_at.isoformat()}.",
        )

    # Check existing session
    sess_res = await db.execute(
        select(ExamSession).where(
            ExamSession.exam_id == exam.id,
            ExamSession.user_id == current_user.id,
        )
    )
    session = sess_res.scalar_one_or_none()

    if session is not None:
        if session.submitted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Exam session has already been submitted.",
            )
        # Check if duration expired during sitting
        sess_started = _to_utc(session.started_at) or now
        duration_delta = timedelta(minutes=exam.duration_minutes)
        if now >= sess_started + duration_delta:
            session.submitted_at = sess_started + duration_delta
            session.is_auto_submitted = True
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Exam session timer expired and was auto-submitted.",
            )
    else:
        # Create new session
        session = ExamSession(
            id=uuid.uuid4(),
            exam_id=exam.id,
            user_id=current_user.id,
            started_at=now,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # Calculate remaining time
    sess_started = _to_utc(session.started_at) or now
    max_duration_end = sess_started + timedelta(minutes=exam.duration_minutes)
    deadline = min(ends_at, max_duration_end) if ends_at else max_duration_end
    remaining_secs = max(0, int((deadline - now).total_seconds()))

    sorted_problems = sorted(exam.problems, key=lambda p: p.order_index)
    problems_resp = [_build_exam_problem_response(ep, conceal=False) for ep in sorted_problems]

    return ExamSessionStartResponse(
        session_id=session.id,
        exam_id=exam.id,
        started_at=session.started_at,
        duration_seconds=exam.duration_minutes * 60,
        remaining_seconds=remaining_secs,
        fullscreen_required=exam.fullscreen_required,
        tab_switch_limit=exam.tab_switch_limit,
        copy_paste_blocked=exam.copy_paste_blocked,
        problems=problems_resp,
    )


@router.post(
    "/exam-sessions/{session_id}/violations",
    response_model=ExamViolationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_exam_violation(
    session_id: uuid.UUID,
    body: ExamViolationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamViolationResponse:
    """Log an anti-cheat violation (tab switch, fullscreen exit, copy/paste, or focus loss)."""
    session = await _get_session_or_404(session_id, db)
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot log violation for another student's exam session.",
        )
    if session.submitted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam session has already been submitted.",
        )

    violation = ExamViolation(
        id=uuid.uuid4(),
        exam_session_id=session.id,
        violation_type=body.violation_type,
        details=body.details,
    )
    db.add(violation)
    await db.commit()
    await db.refresh(violation)

    # Compute violation totals
    res = await db.execute(
        select(ExamViolation).where(ExamViolation.exam_session_id == session.id)
    )
    all_violations = res.scalars().all()
    total_violations = len(all_violations)
    tab_switches = sum(1 for v in all_violations if v.violation_type == "tab_switch")

    exam = session.exam
    tab_switches_remaining = max(0, exam.tab_switch_limit - tab_switches)
    flagged = (tab_switches >= exam.tab_switch_limit)

    return ExamViolationResponse(
        id=violation.id,
        exam_session_id=violation.exam_session_id,
        violation_type=violation.violation_type,
        total_violations=total_violations,
        tab_switches_remaining=tab_switches_remaining,
        flagged=flagged,
        occurred_at=violation.occurred_at,
    )


@router.post(
    "/exams/{exam_id}/submit",
    response_model=ExamSessionSummary,
)
async def submit_exam_session(
    exam_id: uuid.UUID,
    body: ExamSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamSessionSummary:
    """Submit exam session, calculate weighted problem scores, and lock exam."""
    exam = await _get_exam_or_404(exam_id, db)
    await _ensure_course_access(exam.course, current_user, db)

    sess_res = await db.execute(
        select(ExamSession)
        .where(
            ExamSession.exam_id == exam.id,
            ExamSession.user_id == current_user.id,
        )
        .options(selectinload(ExamSession.violations))
    )
    session = sess_res.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active exam session found for this student.",
        )

    now = datetime.now(timezone.utc)
    if session.submitted_at is None:
        session.submitted_at = now
        session.is_auto_submitted = body.is_auto_submitted

    # Compute score per problem based on exam_problems weights
    problem_scores: dict[str, int] = {}
    total_earned = 0
    sess_started = _to_utc(session.started_at) or now

    for ep in exam.problems:
        # Find best submission during this exam session
        sub_res = await db.execute(
            select(Submission)
            .where(
                Submission.problem_id == ep.problem_id,
                Submission.user_id == current_user.id,
            )
            .order_by(Submission.score.desc())
        )
        subs = sub_res.scalars().all()
        valid_subs = [s for s in subs if (_to_utc(s.submitted_at) or now) >= sess_started]
        best_sub = valid_subs[0] if valid_subs else None
        sub_score_pct = (best_sub.score or 0) if best_sub else 0
        points = round((sub_score_pct / 100) * ep.weight)
        problem_scores[str(ep.problem_id)] = points
        total_earned += points

    session.total_score = total_earned
    await db.commit()

    return ExamSessionSummary(
        session_id=session.id,
        exam_id=exam.id,
        submitted_at=session.submitted_at,
        is_auto_submitted=session.is_auto_submitted,
        total_score=session.total_score,
        problem_scores=problem_scores,
        violation_count=len(session.violations),
    )


# ── Results & Integrity Dashboard Endpoints ──────────────────────────────────

@router.get(
    "/exams/{exam_id}/results",
    response_model=ExamResultsDashboard,
)
async def get_exam_results_dashboard(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamResultsDashboard:
    """Full exam results and anti-cheat audit dashboard (Instructor only)."""
    exam = await _get_exam_or_404(exam_id, db)
    _ensure_course_instructor(exam.course, current_user)

    # All enrolled students
    enr_res = await db.execute(
        select(Enrollment)
        .where(Enrollment.course_id == exam.course_id)
        .options(selectinload(Enrollment.user))
    )
    enrollments = enr_res.scalars().all()
    total_enrolled = len(enrollments)

    # Sessions
    sess_res = await db.execute(
        select(ExamSession)
        .where(ExamSession.exam_id == exam.id)
        .options(
            selectinload(ExamSession.user),
            selectinload(ExamSession.violations),
        )
    )
    sessions = {s.user_id: s for s in sess_res.scalars().all()}

    student_results = []
    submitted_scores = []

    for enr in enrollments:
        u = enr.user
        sess = sessions.get(u.id)
        if sess is not None:
            sess_status = "submitted" if sess.submitted_at else "in_progress"
            if sess.submitted_at and sess.total_score is not None:
                submitted_scores.append(sess.total_score)
            violations_data = [
                {
                    "violation_type": v.violation_type,
                    "details": v.details,
                    "occurred_at": v.occurred_at.isoformat(),
                }
                for v in sess.violations
            ]
            student_results.append(
                ExamStudentResult(
                    user_id=u.id,
                    name=u.name,
                    email=u.email,
                    status=sess_status,
                    started_at=sess.started_at,
                    submitted_at=sess.submitted_at,
                    is_auto_submitted=sess.is_auto_submitted,
                    total_score=sess.total_score,
                    violation_count=len(sess.violations),
                    violations=violations_data,
                )
            )
        else:
            student_results.append(
                ExamStudentResult(
                    user_id=u.id,
                    name=u.name,
                    email=u.email,
                    status="not_started",
                    started_at=None,
                    submitted_at=None,
                    is_auto_submitted=False,
                    total_score=None,
                    violation_count=0,
                    violations=[],
                )
            )

    avg_score = round(sum(submitted_scores) / len(submitted_scores), 1) if submitted_scores else 0.0

    return ExamResultsDashboard(
        exam_id=exam.id,
        course_id=exam.course_id,
        title=exam.title,
        total_enrolled=total_enrolled,
        submissions_count=len(submitted_scores),
        average_score=avg_score,
        students=student_results,
    )


@router.get(
    "/exams/{exam_id}/my-result",
    response_model=ExamMyResultResponse,
)
async def get_my_exam_result(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamMyResultResponse:
    """Retrieve the student's own graded exam result."""
    exam = await _get_exam_or_404(exam_id, db)
    await _ensure_course_access(exam.course, current_user, db)

    sess_res = await db.execute(
        select(ExamSession).where(
            ExamSession.exam_id == exam.id,
            ExamSession.user_id == current_user.id,
        )
    )
    session = sess_res.scalar_one_or_none()
    if session is None or session.submitted_at is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed exam session found for your account.",
        )

    # Build problem scores breakdown
    problem_scores: dict[str, int] = {}
    sess_started = _to_utc(session.started_at) or datetime.now(timezone.utc)
    for ep in exam.problems:
        sub_res = await db.execute(
            select(Submission)
            .where(
                Submission.problem_id == ep.problem_id,
                Submission.user_id == current_user.id,
            )
            .order_by(Submission.score.desc())
        )
        subs = sub_res.scalars().all()
        valid_subs = [s for s in subs if (_to_utc(s.submitted_at) or sess_started) >= sess_started]
        best_sub = valid_subs[0] if valid_subs else None
        sub_pct = (best_sub.score or 0) if best_sub else 0
        points = round((sub_pct / 100) * ep.weight)
        problem_scores[str(ep.problem_id)] = points

    return ExamMyResultResponse(
        exam_id=exam.id,
        course_id=exam.course_id,
        total_score=session.total_score or 0,
        submitted_at=session.submitted_at,
        is_auto_submitted=session.is_auto_submitted,
        problem_scores=problem_scores,
    )

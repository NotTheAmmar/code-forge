"""Courses router — course management, enrollment, problem CRUD, and gradebook.

Routes
------
POST   /courses                          → create course (instructor)
GET    /courses                          → list my courses
GET    /courses/{course_id}              → course detail (enrolled)
POST   /courses/{course_id}/join         → join via invite code
GET    /courses/{course_id}/members      → list members (instructor)

POST   /courses/{course_id}/problems     → create problem + test cases (instructor)
GET    /courses/{course_id}/problems     → list problems in course (enrolled)
GET    /courses/{course_id}/problems/{problem_id}   → problem detail (enrolled)
PUT    /problems/{problem_id}            → update problem (instructor)
DELETE /problems/{problem_id}            → delete problem (instructor)
POST   /courses/{course_id}/problems/bulk-import    → bulk import (instructor)

GET    /courses/{course_id}/gradebook    → student × problem score matrix (instructor)
"""

import secrets
import string
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.dependencies import get_current_user, require_instructor
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.course import (
    CourseMemberResponse,
    CourseCreate,
    CourseDetailResponse,
    CourseJoinRequest,
    CourseResponse,
    EnrollmentResponse,
)
from app.schemas.problem import (
    BulkImportRequest,
    BulkImportResponse,
    ProblemCreate,
    ProblemDetail,
    ProblemSummary,
    ProblemUpdate,
    TestCaseCreate,
)

router = APIRouter(tags=["courses"])

# ── Helpers ───────────────────────────────────────────────────────────────────

_INVITE_CHARS = string.ascii_uppercase + string.digits


def _generate_invite_code(length: int = 6) -> str:
    return "".join(secrets.choice(_INVITE_CHARS) for _ in range(length))


async def _get_enrollment_or_403(
    course_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Enrollment:
    """Return the enrollment row or raise 403."""
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


async def _get_course_or_404(course_id: uuid.UUID, db: AsyncSession) -> Course:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )
    return course


async def _get_problem_or_404(problem_id: uuid.UUID, db: AsyncSession) -> Problem:
    result = await db.execute(
        select(Problem)
        .where(Problem.id == problem_id)
        .options(selectinload(Problem.test_cases))
    )
    problem = result.scalar_one_or_none()
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found.",
        )
    return problem


def _build_course_response(
    course: Course,
    enrollment: Enrollment | None,
    member_count: int,
    problem_count: int,
) -> CourseResponse:
    return CourseResponse(
        id=course.id,
        title=course.title,
        description=course.description,
        invite_code=course.invite_code,
        created_by=course.created_by,
        role=enrollment.role if enrollment else None,
        member_count=member_count,
        problem_count=problem_count,
        created_at=course.created_at,
    )


async def _create_problem_with_cases(
    course_id: uuid.UUID,
    created_by: uuid.UUID,
    body: ProblemCreate,
    db: AsyncSession,
) -> Problem:
    """Insert problem + test cases. Returns the new Problem (with test_cases loaded)."""
    # Slug uniqueness check
    existing = await db.execute(select(Problem).where(Problem.slug == body.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A problem with slug '{body.slug}' already exists.",
        )

    problem = Problem(
        id=uuid.uuid4(),
        course_id=course_id,
        created_by=created_by,
        slug=body.slug,
        title=body.title,
        description=body.description,
        difficulty=body.difficulty,
        starter_code_java=body.starter_code_java,
        starter_code_python=body.starter_code_python,
        time_limit_sec=body.time_limit_sec,
        memory_limit_mb=body.memory_limit_mb,
    )
    db.add(problem)
    await db.flush()  # get problem.id without committing

    for tc in body.test_cases:
        db.add(
            TestCase(
                id=uuid.uuid4(),
                problem_id=problem.id,
                label=tc.label,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                is_visible=tc.is_visible,
                order_index=tc.order_index,
            )
        )

    return problem


# ═══════════════════════════════════════════════════════════════════════════════
# Course CRUD
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/courses",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course (instructor only)",
)
async def create_course(
    body: CourseCreate,
    current_user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> CourseResponse:
    """Create a course and auto-enroll the creator as instructor."""
    # Generate a unique invite code (retry on collision — astronomically rare)
    for _ in range(5):
        code = _generate_invite_code()
        existing = await db.execute(select(Course).where(Course.invite_code == code))
        if existing.scalar_one_or_none() is None:
            break
    else:
        raise HTTPException(status_code=500, detail="Could not generate unique invite code.")

    course = Course(
        id=uuid.uuid4(),
        title=body.title,
        description=body.description,
        created_by=current_user.id,
        invite_code=code,
    )
    db.add(course)
    await db.flush()

    enrollment = Enrollment(
        id=uuid.uuid4(),
        user_id=current_user.id,
        course_id=course.id,
        role="instructor",
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(course)

    return _build_course_response(course, enrollment, member_count=1, problem_count=0)


@router.get(
    "/courses",
    response_model=list[CourseResponse],
    summary="List courses the current user is enrolled in",
)
async def list_my_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CourseResponse]:
    """Return all courses the user belongs to, with their role and counts."""
    # Fetch enrollments for this user with the associated course
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.user_id == current_user.id)
        .options(selectinload(Enrollment.course))
    )
    enrollments = result.scalars().all()

    course_ids = [e.course_id for e in enrollments]
    if not course_ids:
        return []

    # Member counts per course
    member_counts_result = await db.execute(
        select(Enrollment.course_id, func.count(Enrollment.id))
        .where(Enrollment.course_id.in_(course_ids))
        .group_by(Enrollment.course_id)
    )
    member_counts: dict[uuid.UUID, int] = dict(member_counts_result.all())

    # Problem counts per course
    problem_counts_result = await db.execute(
        select(Problem.course_id, func.count(Problem.id))
        .where(Problem.course_id.in_(course_ids))
        .group_by(Problem.course_id)
    )
    problem_counts: dict[uuid.UUID, int] = dict(problem_counts_result.all())

    return [
        _build_course_response(
            e.course,
            e,
            member_count=member_counts.get(e.course_id, 0),
            problem_count=problem_counts.get(e.course_id, 0),
        )
        for e in enrollments
    ]


@router.get(
    "/courses/{course_id}",
    response_model=CourseDetailResponse,
    summary="Get course details (enrolled users only)",
)
async def get_course(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseDetailResponse:
    """Return course details. Only enrolled users (or the creator) can access."""
    course = await _get_course_or_404(course_id, db)
    enrollment = await _get_enrollment_or_403(course_id, current_user.id, db)

    member_count_result = await db.execute(
        select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id)
    )
    member_count = member_count_result.scalar_one()

    return CourseDetailResponse(
        id=course.id,
        title=course.title,
        description=course.description,
        invite_code=course.invite_code,
        created_by=course.created_by,
        user_role=enrollment.role,
        member_count=member_count,
        created_at=course.created_at,
    )


@router.post(
    "/courses/{course_id}/join",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join a course using an invite code",
)
async def join_course(
    course_id: uuid.UUID,
    body: CourseJoinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    """Enroll the current user in the course if the invite code matches."""
    course = await _get_course_or_404(course_id, db)

    if course.invite_code.upper() != body.invite_code.upper():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite code.",
        )

    # Idempotent — already enrolled?
    existing = await db.execute(
        select(Enrollment).where(
            Enrollment.course_id == course_id,
            Enrollment.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this course.",
        )

    enrollment = Enrollment(
        id=uuid.uuid4(),
        user_id=current_user.id,
        course_id=course_id,
        role="student",
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)

    return EnrollmentResponse(
        id=enrollment.id,
        course_id=course_id,
        course_title=course.title,
        user_id=current_user.id,
        role=enrollment.role,
        joined_at=enrollment.joined_at,
    )


@router.get(
    "/courses/{course_id}/members",
    response_model=list[CourseMemberResponse],
    summary="List course members (instructor only)",
)
async def list_members(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CourseMemberResponse]:
    """Return all enrolled users. Only instructors of this course can call this."""
    enrollment = await _get_enrollment_or_403(course_id, current_user.id, db)
    if enrollment.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can view the member list.",
        )

    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.course_id == course_id)
        .options(selectinload(Enrollment.user))
        .order_by(Enrollment.joined_at)
    )
    enrollments = result.scalars().all()

    return [
        CourseMemberResponse(
            user_id=e.user_id,
            name=e.user.name,
            email=e.user.email,
            role=e.role,
            joined_at=e.joined_at,
        )
        for e in enrollments
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Problem CRUD (course-scoped)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/courses/{course_id}/problems",
    response_model=ProblemDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a problem in a course (instructor only)",
)
async def create_problem(
    course_id: uuid.UUID,
    body: ProblemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProblemDetail:
    """Create a problem with test cases inside the given course.

    The caller must be an instructor of *this* course (not just any instructor).
    """
    enrollment = await _get_enrollment_or_403(course_id, current_user.id, db)
    if enrollment.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course instructors can create problems.",
        )

    problem = await _create_problem_with_cases(course_id, current_user.id, body, db)
    await db.commit()
    await db.refresh(problem)

    # Eagerly load test_cases for response
    result = await db.execute(
        select(Problem)
        .where(Problem.id == problem.id)
        .options(selectinload(Problem.test_cases))
    )
    problem = result.scalar_one()
    return ProblemDetail.model_validate(problem)


@router.get(
    "/courses/{course_id}/problems",
    response_model=list[ProblemSummary],
    summary="List problems in a course (enrolled users)",
)
async def list_course_problems(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProblemSummary]:
    """Return all problems in the course. User must be enrolled."""
    await _get_enrollment_or_403(course_id, current_user.id, db)

    result = await db.execute(
        select(Problem)
        .where(Problem.course_id == course_id)
        .order_by(Problem.created_at)
    )
    return [ProblemSummary.model_validate(p) for p in result.scalars().all()]


@router.get(
    "/courses/{course_id}/problems/{problem_id}",
    response_model=ProblemDetail,
    summary="Get a problem with test cases (enrolled users)",
)
async def get_course_problem(
    course_id: uuid.UUID,
    problem_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProblemDetail:
    """Return full problem detail for a problem within a course."""
    await _get_enrollment_or_403(course_id, current_user.id, db)

    result = await db.execute(
        select(Problem)
        .where(Problem.id == problem_id, Problem.course_id == course_id)
        .options(selectinload(Problem.test_cases))
    )
    problem = result.scalar_one_or_none()
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found.")
    return ProblemDetail.model_validate(problem)


@router.put(
    "/problems/{problem_id}",
    response_model=ProblemDetail,
    summary="Update a problem (instructor of the course only)",
)
async def update_problem(
    problem_id: uuid.UUID,
    body: ProblemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProblemDetail:
    """Partially update a problem. If test_cases is provided it fully replaces the set."""
    problem = await _get_problem_or_404(problem_id, db)

    # Must be an instructor of the problem's course
    enrollment = await _get_enrollment_or_403(problem.course_id, current_user.id, db)
    if enrollment.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course instructors can update problems.",
        )

    # Apply simple field updates
    for field in ("title", "description", "difficulty", "starter_code_java",
                  "starter_code_python", "time_limit_sec", "memory_limit_mb"):
        value = getattr(body, field)
        if value is not None:
            setattr(problem, field, value)

    # Replace test cases if provided
    if body.test_cases is not None:
        # Delete existing
        for tc in list(problem.test_cases):
            await db.delete(tc)
        await db.flush()
        # Insert new
        for tc in body.test_cases:
            db.add(
                TestCase(
                    id=uuid.uuid4(),
                    problem_id=problem.id,
                    label=tc.label,
                    input_data=tc.input_data,
                    expected_output=tc.expected_output,
                    is_visible=tc.is_visible,
                    order_index=tc.order_index,
                )
            )

    await db.commit()

    # Reload with fresh test_cases
    result = await db.execute(
        select(Problem)
        .where(Problem.id == problem_id)
        .options(selectinload(Problem.test_cases))
    )
    return ProblemDetail.model_validate(result.scalar_one())


@router.delete(
    "/problems/{problem_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a problem (instructor of the course only)",
)
async def delete_problem(
    problem_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a problem and all its test cases (cascade). Submissions are also cascaded."""
    problem = await _get_problem_or_404(problem_id, db)

    enrollment = await _get_enrollment_or_403(problem.course_id, current_user.id, db)
    if enrollment.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course instructors can delete problems.",
        )

    await db.delete(problem)
    await db.commit()


@router.post(
    "/courses/{course_id}/problems/bulk-import",
    response_model=BulkImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk-import problems from a JSON array (instructor only)",
)
async def bulk_import_problems(
    course_id: uuid.UUID,
    body: BulkImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BulkImportResponse:
    """Accept a list of problems and import them all into the course.

    Problems are imported one-by-one. If any individual problem fails (e.g. slug
    conflict) it is skipped and reported in ``errors``, but the rest are still imported.
    """
    enrollment = await _get_enrollment_or_403(course_id, current_user.id, db)
    if enrollment.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course instructors can import problems.",
        )

    imported_slugs: list[str] = []
    errors: list[str] = []

    for pc in body.problems:
        try:
            await _create_problem_with_cases(course_id, current_user.id, pc, db)
            await db.commit()
            imported_slugs.append(pc.slug)
        except HTTPException as exc:
            await db.rollback()
            errors.append(f"{pc.slug}: {exc.detail}")

    return BulkImportResponse(
        imported_count=len(imported_slugs),
        failed_count=len(errors),
        imported_slugs=imported_slugs,
        errors=errors,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Gradebook
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/courses/{course_id}/gradebook",
    summary="Get gradebook — Student × Problem score matrix (instructor only)",
)
async def get_gradebook(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the best score per student per problem as a nested dict.

    Response shape::

        {
          "problems": [{"id": "...", "slug": "...", "title": "..."}],
          "rows": [
            {
              "user_id": "...", "name": "...", "email": "...",
              "scores": {"<problem_id>": 95, ...}
            }
          ]
        }
    """
    enrollment = await _get_enrollment_or_403(course_id, current_user.id, db)
    if enrollment.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course instructors can view the gradebook.",
        )

    # Fetch problems
    prob_result = await db.execute(
        select(Problem)
        .where(Problem.course_id == course_id)
        .order_by(Problem.created_at)
    )
    problems = prob_result.scalars().all()
    problem_ids = [p.id for p in problems]

    # Fetch student enrollments
    student_enr_result = await db.execute(
        select(Enrollment)
        .where(
            Enrollment.course_id == course_id,
            Enrollment.role == "student",
        )
        .options(selectinload(Enrollment.user))
    )
    student_enrollments = student_enr_result.scalars().all()

    if not problem_ids or not student_enrollments:
        return {
            "problems": [{"id": str(p.id), "slug": p.slug, "title": p.title} for p in problems],
            "rows": [],
        }

    student_ids = [e.user_id for e in student_enrollments]

    # Best score per (user_id, problem_id) using a single aggregation query
    score_result = await db.execute(
        select(
            Submission.user_id,
            Submission.problem_id,
            func.max(Submission.score).label("best_score"),
        )
        .where(
            Submission.problem_id.in_(problem_ids),
            Submission.user_id.in_(student_ids),
            Submission.is_full_submit.is_(True),
        )
        .group_by(Submission.user_id, Submission.problem_id)
    )
    # Build lookup: (user_id, problem_id) → best_score
    score_map: dict[tuple, int] = {
        (row.user_id, row.problem_id): row.best_score
        for row in score_result.all()
        if row.best_score is not None
    }

    rows = []
    for enr in student_enrollments:
        rows.append({
            "user_id": str(enr.user_id),
            "name": enr.user.name,
            "email": enr.user.email,
            "scores": {
                str(p.id): score_map.get((enr.user_id, p.id), None)
                for p in problems
            },
        })

    return {
        "problems": [{"id": str(p.id), "slug": p.slug, "title": p.title} for p in problems],
        "rows": rows,
    }

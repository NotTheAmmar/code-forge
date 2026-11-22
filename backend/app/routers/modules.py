"""FastAPI router for Learning Modules, Instructional Contents, and Student Progress.

Endpoints:
    POST   /courses/{course_id}/modules          → create module (instructor)
    GET    /courses/{course_id}/modules          → list modules (enrolled / instructor)
    GET    /modules/{module_id}                  → module detail with contents (enrolled)
    PUT    /modules/{module_id}                  → update module (instructor)
    DELETE /modules/{module_id}                  → delete module (instructor)

    POST   /modules/{module_id}/contents         → add content item (instructor)
    PUT    /contents/{content_id}                → update content item (instructor)
    DELETE /contents/{content_id}                → delete content item (instructor)

    POST   /modules/{module_id}/complete         → mark module complete (student)
    GET    /courses/{course_id}/module-progress  → course module progress (student)
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.dependencies import get_current_user
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.learning_content import LearningContent
from app.models.learning_module import LearningModule
from app.models.module_progress import ModuleProgress
from app.models.problem import Problem
from app.models.user import User
from app.schemas.module import (
    ContentCreate,
    ContentResponse,
    ContentUpdate,
    CourseProgressResponse,
    ModuleCreate,
    ModuleDetailResponse,
    ModuleProgressResponse,
    ModuleProgressUpdate,
    ModuleResponse,
    ModuleUpdate,
)

router = APIRouter(tags=["modules"])


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


async def _get_module_or_404(module_id: uuid.UUID, db: AsyncSession) -> LearningModule:
    res = await db.execute(
        select(LearningModule)
        .where(LearningModule.id == module_id)
        .options(selectinload(LearningModule.contents))
    )
    module = res.scalar_one_or_none()
    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning module '{module_id}' not found.",
        )
    return module


async def _get_content_or_404(content_id: uuid.UUID, db: AsyncSession) -> LearningContent:
    res = await db.execute(
        select(LearningContent)
        .where(LearningContent.id == content_id)
        .options(selectinload(LearningContent.module))
    )
    content = res.scalar_one_or_none()
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning content '{content_id}' not found.",
        )
    return content


async def _ensure_course_access(
    course: Course, current_user: User, db: AsyncSession
) -> None:
    """Allow access if current_user is course creator or enrolled student."""
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
    """Allow mutation only if current_user is an instructor and authored the course."""
    if current_user.role != "instructor" or course.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor access required for this course.",
        )


# ── Module Endpoints ──────────────────────────────────────────────────────────

@router.post(
    "/courses/{course_id}/modules",
    response_model=ModuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_module(
    course_id: uuid.UUID,
    body: ModuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModuleResponse:
    """Create a new learning module (Instructor only)."""
    course = await _get_course_or_404(course_id, db)
    _ensure_course_instructor(course, current_user)

    module = LearningModule(
        id=uuid.uuid4(),
        course_id=course_id,
        title=body.title,
        description=body.description,
        order_index=body.order_index,
        is_published=body.is_published,
        created_by=current_user.id,
    )
    db.add(module)
    await db.commit()
    await db.refresh(module)

    return ModuleResponse(
        id=module.id,
        course_id=module.course_id,
        title=module.title,
        description=module.description,
        order_index=module.order_index,
        is_published=module.is_published,
        content_count=0,
        is_completed=False,
        created_at=module.created_at,
    )


@router.get(
    "/courses/{course_id}/modules",
    response_model=list[ModuleResponse],
)
async def list_course_modules(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ModuleResponse]:
    """List modules for a course with per-student completion status."""
    course = await _get_course_or_404(course_id, db)
    await _ensure_course_access(course, current_user, db)

    is_instructor = (course.created_by == current_user.id)

    # Instructors can see unpublished drafts; students only see published modules
    query = select(LearningModule).where(LearningModule.course_id == course_id)
    if not is_instructor:
        query = query.where(LearningModule.is_published == True)  # noqa: E712
    query = query.order_by(LearningModule.order_index, LearningModule.created_at)

    res = await db.execute(query.options(selectinload(LearningModule.contents)))
    modules = res.scalars().all()

    # Fetch user's completion records
    prog_res = await db.execute(
        select(ModuleProgress.module_id, ModuleProgress.is_completed).where(
            ModuleProgress.user_id == current_user.id,
            ModuleProgress.module_id.in_([m.id for m in modules]),
        )
    )
    completed_map = {row[0]: row[1] for row in prog_res.all()}

    output = []
    for m in modules:
        output.append(
            ModuleResponse(
                id=m.id,
                course_id=m.course_id,
                title=m.title,
                description=m.description,
                order_index=m.order_index,
                is_published=m.is_published,
                content_count=len(m.contents) if m.contents else 0,
                is_completed=completed_map.get(m.id, False),
                created_at=m.created_at,
            )
        )
    return output


@router.get(
    "/modules/{module_id}",
    response_model=ModuleDetailResponse,
)
async def get_module_detail(
    module_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModuleDetailResponse:
    """Get full module details including instructional lessons, videos, and exercises."""
    module = await _get_module_or_404(module_id, db)
    course = await _get_course_or_404(module.course_id, db)
    await _ensure_course_access(course, current_user, db)

    is_instructor = (course.created_by == current_user.id)
    if not is_instructor and not module.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning module '{module_id}' not found.",
        )

    # Check progress
    prog_res = await db.execute(
        select(ModuleProgress.is_completed).where(
            ModuleProgress.module_id == module.id,
            ModuleProgress.user_id == current_user.id,
        )
    )
    is_completed = prog_res.scalar_one_or_none() or False

    sorted_contents = sorted(module.contents, key=lambda c: (c.order_index, c.created_at))
    contents_resp = [
        ContentResponse(
            id=c.id,
            module_id=c.module_id,
            content_type=c.content_type,
            title=c.title,
            body=c.body,
            problem_id=c.problem_id,
            order_index=c.order_index,
            created_at=c.created_at,
        )
        for c in sorted_contents
    ]

    return ModuleDetailResponse(
        id=module.id,
        course_id=module.course_id,
        title=module.title,
        description=module.description,
        order_index=module.order_index,
        is_published=module.is_published,
        content_count=len(sorted_contents),
        is_completed=is_completed,
        created_at=module.created_at,
        contents=contents_resp,
    )


@router.put(
    "/modules/{module_id}",
    response_model=ModuleResponse,
)
async def update_module(
    module_id: uuid.UUID,
    body: ModuleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModuleResponse:
    """Update a learning module (Instructor only)."""
    module = await _get_module_or_404(module_id, db)
    course = await _get_course_or_404(module.course_id, db)
    _ensure_course_instructor(course, current_user)

    if body.title is not None:
        module.title = body.title
    if body.description is not None:
        module.description = body.description
    if body.order_index is not None:
        module.order_index = body.order_index
    if body.is_published is not None:
        module.is_published = body.is_published

    await db.commit()
    await db.refresh(module)

    return ModuleResponse(
        id=module.id,
        course_id=module.course_id,
        title=module.title,
        description=module.description,
        order_index=module.order_index,
        is_published=module.is_published,
        content_count=len(module.contents) if module.contents else 0,
        is_completed=False,
        created_at=module.created_at,
    )


@router.delete(
    "/modules/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_module(
    module_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a learning module and all nested contents (Instructor only)."""
    module = await _get_module_or_404(module_id, db)
    course = await _get_course_or_404(module.course_id, db)
    _ensure_course_instructor(course, current_user)

    await db.delete(module)
    await db.commit()


# ── Content Item Endpoints ────────────────────────────────────────────────────

@router.post(
    "/modules/{module_id}/contents",
    response_model=ContentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_module_content(
    module_id: uuid.UUID,
    body: ContentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentResponse:
    """Add a content item (text, video, or practice problem) to a module (Instructor only)."""
    module = await _get_module_or_404(module_id, db)
    course = await _get_course_or_404(module.course_id, db)
    _ensure_course_instructor(course, current_user)

    if body.content_type == "problem" and body.problem_id is not None:
        prob_res = await db.execute(select(Problem).where(Problem.id == body.problem_id))
        if prob_res.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Problem '{body.problem_id}' not found.",
            )

    content = LearningContent(
        id=uuid.uuid4(),
        module_id=module_id,
        content_type=body.content_type,
        title=body.title,
        body=body.body,
        problem_id=body.problem_id,
        order_index=body.order_index,
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)

    return ContentResponse.model_validate(content)


@router.put(
    "/contents/{content_id}",
    response_model=ContentResponse,
)
async def update_content(
    content_id: uuid.UUID,
    body: ContentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentResponse:
    """Update a content item (Instructor only)."""
    content = await _get_content_or_404(content_id, db)
    course = await _get_course_or_404(content.module.course_id, db)
    _ensure_course_instructor(course, current_user)

    if body.content_type is not None:
        content.content_type = body.content_type
    if body.title is not None:
        content.title = body.title
    if body.body is not None:
        content.body = body.body
    if body.order_index is not None:
        content.order_index = body.order_index
    if body.problem_id is not None:
        prob_res = await db.execute(select(Problem).where(Problem.id == body.problem_id))
        if prob_res.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Problem '{body.problem_id}' not found.",
            )
        content.problem_id = body.problem_id

    await db.commit()
    await db.refresh(content)
    return ContentResponse.model_validate(content)


@router.delete(
    "/contents/{content_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_content(
    content_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a content item (Instructor only)."""
    content = await _get_content_or_404(content_id, db)
    course = await _get_course_or_404(content.module.course_id, db)
    _ensure_course_instructor(course, current_user)

    await db.delete(content)
    await db.commit()


# ── Student Progress Tracking ─────────────────────────────────────────────────

@router.post(
    "/modules/{module_id}/complete",
    response_model=ModuleProgressResponse,
)
async def complete_module(
    module_id: uuid.UUID,
    body: ModuleProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModuleProgressResponse:
    """Mark a module as completed by the student."""
    module = await _get_module_or_404(module_id, db)
    course = await _get_course_or_404(module.course_id, db)
    await _ensure_course_access(course, current_user, db)

    prog_res = await db.execute(
        select(ModuleProgress).where(
            ModuleProgress.module_id == module_id,
            ModuleProgress.user_id == current_user.id,
        )
    )
    progress = prog_res.scalar_one_or_none()
    now_dt = datetime.now(timezone.utc)

    if progress is None:
        progress = ModuleProgress(
            id=uuid.uuid4(),
            module_id=module_id,
            user_id=current_user.id,
            content_id=body.last_content_id,
            is_completed=True,
            completed_at=now_dt,
        )
        db.add(progress)
    else:
        progress.is_completed = True
        progress.completed_at = now_dt
        if body.last_content_id:
            progress.content_id = body.last_content_id

    await db.commit()
    await db.refresh(progress)

    return ModuleProgressResponse(
        module_id=progress.module_id,
        user_id=progress.user_id,
        is_completed=progress.is_completed,
        completed_at=progress.completed_at,
    )


@router.get(
    "/courses/{course_id}/module-progress",
    response_model=CourseProgressResponse,
)
async def get_course_module_progress(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseProgressResponse:
    """Get the student's progress across all published modules in a course."""
    course = await _get_course_or_404(course_id, db)
    await _ensure_course_access(course, current_user, db)

    # All published modules in course
    mod_res = await db.execute(
        select(LearningModule.id).where(
            LearningModule.course_id == course_id,
            LearningModule.is_published == True,  # noqa: E712
        )
    )
    module_ids = [row[0] for row in mod_res.all()]
    total_count = len(module_ids)

    # Completed modules for student
    completed_ids = []
    if total_count > 0:
        comp_res = await db.execute(
            select(ModuleProgress.module_id).where(
                ModuleProgress.user_id == current_user.id,
                ModuleProgress.module_id.in_(module_ids),
                ModuleProgress.is_completed == True,  # noqa: E712
            )
        )
        completed_ids = [row[0] for row in comp_res.all()]

    completed_count = len(completed_ids)
    pct = round((completed_count / total_count) * 100, 1) if total_count > 0 else 0.0

    return CourseProgressResponse(
        course_id=course_id,
        total_modules=total_count,
        completed_modules=completed_count,
        progress_percentage=pct,
        completed_module_ids=completed_ids,
    )

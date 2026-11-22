"""Unit & integration tests for Phase A3: Learning Modules System.

Tests full module CRUD, content management (text, video, problem),
permission boundaries (instructor vs enrolled student vs unenrolled),
and student completion progress tracking.
"""

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.dependencies import get_db
from app.main import app
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.problem import Problem
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password

# ── SQLite Database Setup for isolated testing ────────────────────────────────

_INSTR_ID = uuid.uuid4()
_STUDENT_ID = uuid.uuid4()
_UNENROLLED_ID = uuid.uuid4()

_INSTR_USER = User(
    id=_INSTR_ID,
    email="instr@modules-test.com",
    name="Prof. Module Master",
    role="instructor",
    password_hash=hash_password("pw"),
)

_STUDENT_USER = User(
    id=_STUDENT_ID,
    email="student@modules-test.com",
    name="Student Learner",
    role="student",
    password_hash=hash_password("pw"),
)

_UNENROLLED_USER = User(
    id=_UNENROLLED_ID,
    email="outsider@modules-test.com",
    name="Outsider",
    role="student",
    password_hash=hash_password("pw"),
)


@pytest.fixture(scope="module")
def mod_engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture(scope="module", autouse=True)
def mod_create_tables(mod_engine):
    async def _init():
        async with mod_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(mod_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add_all([_INSTR_USER, _STUDENT_USER, _UNENROLLED_USER])
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_init())
    yield
    asyncio.get_event_loop().run_until_complete(mod_engine.dispose())


@pytest.fixture
def mod_session_factory(mod_engine):
    return async_sessionmaker(mod_engine, expire_on_commit=False)


@pytest.fixture(scope="module", autouse=True)
def override_db(mod_engine):
    session_factory = async_sessionmaker(mod_engine, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def _make_client(user: User) -> TestClient:
    token = create_access_token(str(user.id), user.role)
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
def instr_client():
    with _make_client(_INSTR_USER) as c:
        yield c


@pytest.fixture
def student_client():
    with _make_client(_STUDENT_USER) as c:
        yield c


@pytest.fixture
def unenrolled_client():
    with _make_client(_UNENROLLED_USER) as c:
        yield c


@pytest.fixture
def setup_course_and_student(mod_session_factory):
    """Sets up a test course with an enrolled student."""
    course_id = uuid.uuid4()
    problem_id = uuid.uuid4()

    async def _setup():
        async with mod_session_factory() as session:
            course = Course(
                id=course_id,
                title="Python & Data Structures",
                description="Core CS curriculum",
                invite_code=f"MOD{uuid.uuid4().hex[:6]}",
                created_by=_INSTR_ID,
            )
            session.add(course)

            enrollment = Enrollment(
                id=uuid.uuid4(),
                course_id=course_id,
                user_id=_STUDENT_ID,
                role="student",
            )
            session.add(enrollment)

            prob = Problem(
                id=problem_id,
                course_id=course_id,
                slug=f"sample-prob-{uuid.uuid4().hex[:6]}",
                title="Sample Problem",
                description="Introductory problem",
                difficulty="easy",
                time_limit_sec=5,
            )
            session.add(prob)
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_setup())
    return {"course_id": course_id, "problem_id": problem_id}


# ── Module CRUD Tests ─────────────────────────────────────────────────────────

def test_instructor_can_create_module(instr_client, student_client, setup_course_and_student):
    course_id = setup_course_and_student["course_id"]

    # 1. Instructor creates module
    payload = {
        "title": "Module 1: Getting Started",
        "description": "Environment setup and basic syntax",
        "order_index": 1,
        "is_published": True,
    }
    resp = instr_client.post(f"/api/v1/courses/{course_id}/modules", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == payload["title"]
    assert data["is_published"] is True
    assert data["content_count"] == 0
    assert data["is_completed"] is False

    # 2. Student cannot create module (403)
    stu_resp = student_client.post(f"/api/v1/courses/{course_id}/modules", json=payload)
    assert stu_resp.status_code == 403


def test_list_modules_and_access_control(instr_client, student_client, unenrolled_client, setup_course_and_student):
    course_id = setup_course_and_student["course_id"]

    # First create a published module
    instr_client.post(
        f"/api/v1/courses/{course_id}/modules",
        json={"title": "Published Module", "order_index": 1, "is_published": True},
    )

    # Enrolled student can list modules
    res = student_client.get(f"/api/v1/courses/{course_id}/modules")
    assert res.status_code == 200
    modules = res.json()
    assert isinstance(modules, list)
    assert len(modules) >= 1

    # Unenrolled student gets 403
    un_res = unenrolled_client.get(f"/api/v1/courses/{course_id}/modules")
    assert un_res.status_code == 403


def test_update_and_delete_module(instr_client, student_client, setup_course_and_student):
    course_id = setup_course_and_student["course_id"]

    # Create temporary module
    create_resp = instr_client.post(
        f"/api/v1/courses/{course_id}/modules",
        json={"title": "Temporary Module", "order_index": 99},
    )
    assert create_resp.status_code == 201
    mod_id = create_resp.json()["id"]

    # Student cannot update (403)
    s_up = student_client.put(f"/api/v1/modules/{mod_id}", json={"title": "Hacked Title"})
    assert s_up.status_code == 403

    # Instructor updates module
    up_resp = instr_client.put(
        f"/api/v1/modules/{mod_id}",
        json={"title": "Updated Temp Module", "is_published": False},
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["title"] == "Updated Temp Module"
    assert up_resp.json()["is_published"] is False

    # Student cannot delete (403)
    s_del = student_client.delete(f"/api/v1/modules/{mod_id}")
    assert s_del.status_code == 403

    # Instructor deletes module
    del_resp = instr_client.delete(f"/api/v1/modules/{mod_id}")
    assert del_resp.status_code == 204

    # Now 404
    get_res = instr_client.get(f"/api/v1/modules/{mod_id}")
    assert get_res.status_code == 404


# ── Content CRUD Tests ────────────────────────────────────────────────────────

def test_content_management_flow(instr_client, student_client, setup_course_and_student):
    course_id = setup_course_and_student["course_id"]
    problem_id = str(setup_course_and_student["problem_id"])

    # 1. Create a module
    mod_resp = instr_client.post(
        f"/api/v1/courses/{course_id}/modules",
        json={"title": "Module with Content", "order_index": 2, "is_published": True},
    )
    assert mod_resp.status_code == 201
    mod_id = mod_resp.json()["id"]

    # 2. Add Text content
    text_resp = instr_client.post(
        f"/api/v1/modules/{mod_id}/contents",
        json={
            "content_type": "text",
            "title": "Lesson 1: Theory",
            "body": "## Markdown Content\nVariables and scoping.",
            "order_index": 1,
        },
    )
    assert text_resp.status_code == 201
    text_data = text_resp.json()
    assert text_data["content_type"] == "text"
    assert text_data["title"] == "Lesson 1: Theory"
    text_id = text_data["id"]

    # 3. Add Video content
    video_resp = instr_client.post(
        f"/api/v1/modules/{mod_id}/contents",
        json={
            "content_type": "video",
            "title": "Lesson 2: Lecture Video",
            "body": "https://www.youtube.com/watch?v=kqtD5dpn9C8",
            "order_index": 2,
        },
    )
    assert video_resp.status_code == 201
    assert video_resp.json()["content_type"] == "video"

    # 4. Add Problem content
    prob_resp = instr_client.post(
        f"/api/v1/modules/{mod_id}/contents",
        json={
            "content_type": "problem",
            "title": "Lesson 3: Coding Exercise",
            "body": "Solve this practice challenge.",
            "problem_id": problem_id,
            "order_index": 3,
        },
    )
    assert prob_resp.status_code == 201
    assert prob_resp.json()["problem_id"] == problem_id

    # 5. Invalid problem_id returns 404
    bad_prob = instr_client.post(
        f"/api/v1/modules/{mod_id}/contents",
        json={
            "content_type": "problem",
            "title": "Bad Problem",
            "problem_id": str(uuid.uuid4()),
        },
    )
    assert bad_prob.status_code == 404

    # 6. Student gets module detail with all 3 contents in order
    det_resp = student_client.get(f"/api/v1/modules/{mod_id}")
    assert det_resp.status_code == 200
    det_data = det_resp.json()
    assert det_data["content_count"] == 3
    assert len(det_data["contents"]) == 3
    assert det_data["contents"][0]["content_type"] == "text"
    assert det_data["contents"][1]["content_type"] == "video"
    assert det_data["contents"][2]["content_type"] == "problem"

    # 7. Update content
    up_resp = instr_client.put(
        f"/api/v1/contents/{text_id}",
        json={"title": "Lesson 1: Advanced Theory"},
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["title"] == "Lesson 1: Advanced Theory"

    # 8. Delete content
    del_resp = instr_client.delete(f"/api/v1/contents/{text_id}")
    assert del_resp.status_code == 204

    det_after = student_client.get(f"/api/v1/modules/{mod_id}")
    assert det_after.json()["content_count"] == 2


# ── Progress Tracking Tests ───────────────────────────────────────────────────

def test_student_progress_and_course_completion(instr_client, student_client, setup_course_and_student):
    course_id = setup_course_and_student["course_id"]

    # Create module
    m_resp = instr_client.post(
        f"/api/v1/courses/{course_id}/modules",
        json={"title": "Progress Test Module", "order_index": 1, "is_published": True},
    )
    mod_id = m_resp.json()["id"]

    # Initial course progress: 0% completed
    prog_before = student_client.get(f"/api/v1/courses/{course_id}/module-progress")
    assert prog_before.status_code == 200
    data_before = prog_before.json()
    assert data_before["completed_modules"] == 0

    # Student marks module as complete
    comp_resp = student_client.post(
        f"/api/v1/modules/{mod_id}/complete",
        json={"last_content_id": None},
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["module_id"] == mod_id
    assert comp_data["is_completed"] is True
    assert comp_data["completed_at"] is not None

    # Check course progress again
    prog_after = student_client.get(f"/api/v1/courses/{course_id}/module-progress")
    assert prog_after.status_code == 200
    data_after = prog_after.json()
    assert data_after["completed_modules"] >= 1
    assert data_after["progress_percentage"] > 0
    assert mod_id in data_after["completed_module_ids"]

    # Module list reflects is_completed: true for student
    list_resp = student_client.get(f"/api/v1/courses/{course_id}/modules")
    assert list_resp.status_code == 200
    matched = next((m for m in list_resp.json() if m["id"] == mod_id), None)
    assert matched is not None
    assert matched["is_completed"] is True

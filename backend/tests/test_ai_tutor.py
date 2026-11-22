"""Unit & integration tests for AI Socratic Tutor & Exam Lockdown Guarantees."""

import asyncio
import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.dependencies import get_db
from app.main import app
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.problem import Problem
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password

_STUDENT_ID = uuid.uuid4()
_STUDENT_USER = User(
    id=_STUDENT_ID,
    email="student@tutor-test.com",
    name="Tutor Test Student",
    role="student",
    password_hash=hash_password("pw"),
)


def _run_coroutine(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@pytest.fixture(scope="module")
def tutor_engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture(scope="module", autouse=True)
def tutor_create_tables(tutor_engine):
    async def _init():
        async with tutor_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(tutor_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(_STUDENT_USER)
            await session.commit()

    _run_coroutine(_init())
    yield
    _run_coroutine(tutor_engine.dispose())


@pytest.fixture(scope="module")
def tutor_session_factory(tutor_engine):
    return async_sessionmaker(tutor_engine, expire_on_commit=False)


@pytest.fixture
def db_session(tutor_session_factory):
    session = tutor_session_factory()
    yield session
    _run_coroutine(session.close())


@pytest.fixture
def client(tutor_session_factory):
    async def override_get_db() -> AsyncSession:
        async with tutor_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def auth_headers():
    token = create_access_token(user_id=str(_STUDENT_ID), role="student")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def setup_problem(tutor_session_factory):
    prob_id = uuid.uuid4()
    course_id = uuid.uuid4()
    slug = f"sample-prob-{uuid.uuid4().hex[:6]}"

    async def _setup():
        async with tutor_session_factory() as session:
            course = Course(
                id=course_id,
                title="Intro CS",
                created_by=_STUDENT_ID,
                invite_code=f"JC{uuid.uuid4().hex[:4]}",
            )
            session.add(course)
            p = Problem(
                id=prob_id,
                course_id=course_id,
                slug=slug,
                title="Sample Two Sum Problem",
                difficulty="easy",
                description="Find two numbers that add up to the target integer.",
                time_limit_sec=2.0,
                memory_limit_mb=128,
            )
            session.add(p)
            session.add(Enrollment(id=uuid.uuid4(), course_id=course_id, user_id=_STUDENT_ID, role="student"))
            await session.commit()

    _run_coroutine(_setup())
    return {"problem_id": prob_id, "slug": slug, "course_id": course_id}


def test_ai_tutor_pedagogical_guidance_success(client, auth_headers, setup_problem):
    slug = setup_problem["slug"]
    payload = {
        "message": "Can you explain the logic to solve this problem?",
        "language": "python",
        "source_code": "def solution():\n    pass",
    }
    resp = client.post(f"/api/v1/problems/{slug}/ai-tutor", json=payload, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "reply" in data
    assert "model" in data
    assert len(data["reply"]) > 50
    # Must NOT give away full code solutions
    assert "def solution():" not in data["reply"]


def test_ai_tutor_forbidden_when_exam_session_id_provided(client, auth_headers, setup_problem):
    slug = setup_problem["slug"]
    fake_exam_session = str(uuid.uuid4())
    payload = {
        "message": "Help me during my exam!",
        "language": "python",
        "exam_session_id": fake_exam_session,
    }
    resp = client.post(f"/api/v1/problems/{slug}/ai-tutor", json=payload, headers=auth_headers)
    assert resp.status_code == 403
    assert "disabled during proctored assessment" in resp.json()["detail"].lower()


def test_ai_tutor_forbidden_when_active_exam_in_progress(client, auth_headers, setup_problem, tutor_session_factory):
    # Create an active exam session in DB for this student
    exam_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async def _create_active_exam():
        async with tutor_session_factory() as session:
            exam = Exam(
                id=exam_id,
                course_id=setup_problem["course_id"],
                title="Active Exam",
                duration_minutes=60,
                starts_at=datetime.now(timezone.utc),
                ends_at=datetime.now(timezone.utc),
            )
            sess = ExamSession(
                id=session_id,
                exam_id=exam_id,
                user_id=_STUDENT_ID,
                started_at=datetime.now(timezone.utc),
                submitted_at=None,  # Active / in-progress!
            )
            session.add(exam)
            session.add(sess)
            await session.commit()

    _run_coroutine(_create_active_exam())

    slug = setup_problem["slug"]
    payload = {
        "message": "Give me a hint please!",
        "language": "python",
    }
    # Even without passing exam_session_id, backend detects student is currently in an exam
    resp = client.post(f"/api/v1/problems/{slug}/ai-tutor", json=payload, headers=auth_headers)
    assert resp.status_code == 403
    assert "locked while an exam session is in progress" in resp.json()["detail"].lower()


def test_ai_tutor_unauthenticated_rejected(client, setup_problem):
    slug = setup_problem["slug"]
    resp = client.post(f"/api/v1/problems/{slug}/ai-tutor", json={"message": "Help"})
    assert resp.status_code in (401, 403)

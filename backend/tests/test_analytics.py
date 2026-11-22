"""Unit & integration tests for Phase A5: Performance Analytics Endpoints.

Tests course-wide metrics, error distribution, student progress tracking,
and problem-level submission analytics.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.dependencies import get_db
from app.main import app
from app.models.badge import Badge
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lab_session import LabSession
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.test_case import TestCase as TestCaseModel
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password

TestCaseModel.__test__ = False


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


# ── Fixtures & DB ─────────────────────────────────────────────────────────────

_INSTR_ID = uuid.uuid4()
_STUDENT_ID = uuid.uuid4()
_OUTSIDER_ID = uuid.uuid4()

_INSTR_USER = User(
    id=_INSTR_ID,
    email="prof@analytics-test.com",
    name="Prof. Analytics",
    role="instructor",
    password_hash=hash_password("pw"),
)

_STUDENT_USER = User(
    id=_STUDENT_ID,
    email="student@analytics-test.com",
    name="Student Alpha",
    role="student",
    password_hash=hash_password("pw"),
)

_OUTSIDER_USER = User(
    id=_OUTSIDER_ID,
    email="outsider@analytics-test.com",
    name="Outsider",
    role="student",
    password_hash=hash_password("pw"),
)


@pytest.fixture(scope="module")
def analytics_engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture(scope="module", autouse=True)
def analytics_create_tables(analytics_engine):
    async def _init():
        async with analytics_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(analytics_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add_all([_INSTR_USER, _STUDENT_USER, _OUTSIDER_USER])
            await session.commit()

    _run_coroutine(_init())
    yield
    _run_coroutine(analytics_engine.dispose())


@pytest.fixture
def analytics_session_factory(analytics_engine):
    return async_sessionmaker(analytics_engine, expire_on_commit=False)


@pytest.fixture(scope="module", autouse=True)
def override_db(analytics_engine):
    session_factory = async_sessionmaker(analytics_engine, expire_on_commit=False)

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
def outsider_client():
    with _make_client(_OUTSIDER_USER) as c:
        yield c


@pytest.fixture
def seeded_analytics_data(analytics_session_factory):
    course_id = uuid.uuid4()
    p1_id = uuid.uuid4()
    p2_id = uuid.uuid4()
    student_id = uuid.uuid4()
    student_user = User(
        id=student_id,
        email=f"stud_{uuid.uuid4().hex[:6]}@analytics-test.com",
        name="Student Alpha",
        role="student",
        password_hash=hash_password("pw"),
    )

    async def _setup():
        now = datetime.now(timezone.utc)
        async with analytics_session_factory() as session:
            session.add(student_user)
            course = Course(
                id=course_id,
                title="Data Structures & Algorithms Analytics",
                description="Analytics test course",
                invite_code=f"AN{uuid.uuid4().hex[:6]}",
                created_by=_INSTR_ID,
            )
            session.add(course)

            p1 = Problem(
                id=p1_id,
                course_id=course_id,
                slug=f"analytics-prob-1-{uuid.uuid4().hex[:6]}",
                title="Analytics Problem 1",
                description="Desc 1",
                difficulty="easy",
                starter_code_java="class Solution {}",
                time_limit_sec=5,
            )
            p2 = Problem(
                id=p2_id,
                course_id=course_id,
                slug=f"analytics-prob-2-{uuid.uuid4().hex[:6]}",
                title="Analytics Problem 2",
                description="Desc 2",
                difficulty="hard",
                starter_code_java="class Solution {}",
                time_limit_sec=5,
            )
            session.add_all([p1, p2])

            session.add(Enrollment(id=uuid.uuid4(), course_id=course_id, user_id=student_id, role="student"))

            # Add submissions
            # Student solves p1 (accepted)
            session.add(
                Submission(
                    id=uuid.uuid4(),
                    problem_id=p1_id,
                    user_id=student_id,
                    language="python",
                    source_code="print('ok')",
                    status="accepted",
                    score=100,
                    execution_time_ms=25,
                    submitted_at=now - timedelta(days=1),
                )
            )
            # Student fails p2 (wrong_answer, score 40)
            session.add(
                Submission(
                    id=uuid.uuid4(),
                    problem_id=p2_id,
                    user_id=student_id,
                    language="c",
                    source_code="printf('wa')",
                    status="wrong_answer",
                    score=40,
                    execution_time_ms=15,
                    submitted_at=now - timedelta(hours=3),
                )
            )
            # Student fails p2 (compile_error)
            session.add(
                Submission(
                    id=uuid.uuid4(),
                    problem_id=p2_id,
                    user_id=student_id,
                    language="cpp",
                    source_code="syntax err",
                    status="compile_error",
                    score=0,
                    execution_time_ms=0,
                    submitted_at=now - timedelta(hours=1),
                )
            )

            # Lab session and badge for student
            lab_id = uuid.uuid4()
            session.add(
                LabSession(
                    id=lab_id,
                    course_id=course_id,
                    title="Analytics Lab",
                    starts_at=now - timedelta(days=2),
                    ends_at=now + timedelta(days=2),
                    mandatory_count=1,
                    is_active=True,
                )
            )
            session.add(
                Badge(
                    id=uuid.uuid4(),
                    user_id=student_id,
                    lab_session_id=lab_id,
                    problem_id=p1_id,
                )
            )

            await session.commit()

    _run_coroutine(_setup())
    return {
        "course_id": course_id,
        "p1_id": p1_id,
        "p2_id": p2_id,
        "student_id": student_id,
        "student_user": student_user,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_course_analytics_instructor_success(instr_client, seeded_analytics_data):
    data = seeded_analytics_data
    resp = instr_client.get(f"/api/v1/courses/{data['course_id']}/analytics")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["course_id"] == str(data["course_id"])
    summary = body["summary"]
    assert summary["total_students"] == 1
    assert summary["total_submissions"] == 3
    # 1 accepted out of 3 -> 33.3%
    assert 30 <= summary["average_pass_rate"] <= 35
    assert summary["active_students_7d"] == 1

    # Check problem pass rates
    prob_stats = {p["problem_id"]: p for p in body["problem_pass_rates"]}
    assert str(data["p1_id"]) in prob_stats
    assert prob_stats[str(data["p1_id"])]["pass_rate"] == 100.0
    assert prob_stats[str(data["p2_id"])]["pass_rate"] == 0.0

    # Check error distribution
    errors = {e["error_type"]: e["count"] for e in body["common_error_distribution"]}
    assert errors.get("wrong_answer") == 1
    assert errors.get("compile_error") == 1


def test_course_analytics_student_forbidden(student_client, seeded_analytics_data):
    data = seeded_analytics_data
    resp = student_client.get(f"/api/v1/courses/{data['course_id']}/analytics")
    assert resp.status_code == 403


def test_student_analytics_self_and_instructor(
    instr_client, outsider_client, seeded_analytics_data
):
    data = seeded_analytics_data
    student_client = _make_client(data["student_user"])
    student_id = data["student_id"]

    # Student viewing own analytics
    resp = student_client.get(f"/api/v1/courses/{data['course_id']}/analytics/students/{student_id}")
    assert resp.status_code == 200, resp.text
    analytics = resp.json()
    assert analytics["user_id"] == str(student_id)
    assert analytics["name"] == "Student Alpha"
    assert analytics["total_submissions"] == 3
    assert analytics["problems_solved"] == 1
    assert analytics["badges_earned"] == 1
    assert len(analytics["score_progression"]) == 3

    # Instructor viewing student's analytics
    inst_resp = instr_client.get(f"/api/v1/courses/{data['course_id']}/analytics/students/{student_id}")
    assert inst_resp.status_code == 200

    # Another student (outsider) attempting to view -> 403
    bad_resp = outsider_client.get(f"/api/v1/courses/{data['course_id']}/analytics/students/{student_id}")
    assert bad_resp.status_code == 403


def test_problem_analytics(instr_client, student_client, seeded_analytics_data):
    data = seeded_analytics_data

    # By UUID
    resp = instr_client.get(f"/api/v1/problems/{data['p2_id']}/analytics")
    assert resp.status_code == 200, resp.text
    p2_stats = resp.json()
    assert p2_stats["problem_id"] == str(data["p2_id"])
    assert p2_stats["total_submissions"] == 2
    assert p2_stats["unique_students"] == 1
    assert p2_stats["pass_rate"] == 0.0
    assert p2_stats["language_breakdown"]["c"] == 1
    assert p2_stats["language_breakdown"]["cpp"] == 1

    # Student cannot view problem instructor analytics
    bad_resp = student_client.get(f"/api/v1/problems/{data['p2_id']}/analytics")
    assert bad_resp.status_code == 403

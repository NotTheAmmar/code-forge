"""Unit & integration tests for Phase A4: Proctored Exam System.

Tests proctored exam creation, configuration, student sitting lifecycle,
anti-cheat violation tracking, weighted scoring, and instructor audit dashboard.
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
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.test_case import TestCase as TestCaseModel
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password

TestCaseModel.__test__ = False

# ── SQLite Database Setup for isolated testing ────────────────────────────────

_INSTR_ID = uuid.uuid4()
_STUDENT_ID = uuid.uuid4()
_STUDENT2_ID = uuid.uuid4()
_OUTSIDER_ID = uuid.uuid4()

_INSTR_USER = User(
    id=_INSTR_ID,
    email="instr@exams-test.com",
    name="Prof. Exam Master",
    role="instructor",
    password_hash=hash_password("pw"),
)

_STUDENT_USER = User(
    id=_STUDENT_ID,
    email="student@exams-test.com",
    name="Exam Candidate One",
    role="student",
    password_hash=hash_password("pw"),
)

_STUDENT2_USER = User(
    id=_STUDENT2_ID,
    email="student2@exams-test.com",
    name="Exam Candidate Two",
    role="student",
    password_hash=hash_password("pw"),
)

_OUTSIDER_USER = User(
    id=_OUTSIDER_ID,
    email="outsider@exams-test.com",
    name="Outsider",
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
def exam_engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture(scope="module", autouse=True)
def exam_create_tables(exam_engine):
    async def _init():
        async with exam_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(exam_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add_all([_INSTR_USER, _STUDENT_USER, _STUDENT2_USER, _OUTSIDER_USER])
            await session.commit()

    _run_coroutine(_init())
    yield
    _run_coroutine(exam_engine.dispose())


@pytest.fixture
def exam_session_factory(exam_engine):
    return async_sessionmaker(exam_engine, expire_on_commit=False)


@pytest.fixture(scope="module", autouse=True)
def override_db(exam_engine):
    session_factory = async_sessionmaker(exam_engine, expire_on_commit=False)

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
def student2_client():
    with _make_client(_STUDENT2_USER) as c:
        yield c


@pytest.fixture
def outsider_client():
    with _make_client(_OUTSIDER_USER) as c:
        yield c


# ── Course & Problem Fixture ──────────────────────────────────────────────────

@pytest.fixture
def setup_course_and_problems(exam_session_factory):
    course_id = uuid.uuid4()
    p1_id = uuid.uuid4()
    p2_id = uuid.uuid4()

    async def _setup():
        async with exam_session_factory() as session:
            course = Course(
                id=course_id,
                title="Algorithms & Proctoring 101",
                description="Proctored assessment course",
                invite_code=f"EX{uuid.uuid4().hex[:6]}",
                created_by=_INSTR_ID,
            )
            session.add(course)

            p1 = Problem(
                id=p1_id,
                course_id=course_id,
                slug=f"problem-one-{uuid.uuid4().hex[:6]}",
                title="Problem One - Arithmetic",
                description="Calculate addition of two numbers",
                difficulty="easy",
                starter_code_java="class Solution {}",
                starter_code_python="def solve(a, b): return a + b",
                time_limit_sec=5,
                memory_limit_mb=128,
            )
            p2 = Problem(
                id=p2_id,
                course_id=course_id,
                slug=f"problem-two-{uuid.uuid4().hex[:6]}",
                title="Problem Two - Arrays",
                description="Find subarray with target sum",
                difficulty="medium",
                starter_code_java="class Solution {}",
                starter_code_python="def find_sub(arr, k): return []",
                time_limit_sec=5,
                memory_limit_mb=256,
            )
            session.add_all([p1, p2])

            session.add(Enrollment(id=uuid.uuid4(), course_id=course_id, user_id=_STUDENT_ID, role="student"))
            session.add(Enrollment(id=uuid.uuid4(), course_id=course_id, user_id=_STUDENT2_ID, role="student"))
            await session.commit()

    _run_coroutine(_setup())
    return {
        "course_id": course_id,
        "p1_id": p1_id,
        "p2_id": p2_id,
    }


# ── Test Cases ────────────────────────────────────────────────────────────────

def test_create_exam_instructor_success(instr_client, setup_course_and_problems):
    data = setup_course_and_problems

    now = datetime.now(timezone.utc)
    payload = {
        "title": "Midterm Exam 2026",
        "description": "Midterm test for AP101",
        "duration_minutes": 60,
        "starts_at": now.isoformat(),
        "ends_at": (now + timedelta(hours=3)).isoformat(),
        "is_active": True,
        "fullscreen_required": True,
        "tab_switch_limit": 3,
        "copy_paste_blocked": True,
        "problems": [
            {"problem_id": str(data["p1_id"]), "order_index": 0, "weight": 40},
            {"problem_id": str(data["p2_id"]), "order_index": 1, "weight": 60},
        ],
    }

    resp = instr_client.post(f"/api/v1/courses/{data['course_id']}/exams", json=payload)
    assert resp.status_code == 201, resp.text
    exam = resp.json()
    assert exam["title"] == "Midterm Exam 2026"
    assert exam["fullscreen_required"] is True
    assert exam["tab_switch_limit"] == 3
    assert len(exam["problems"]) == 2
    assert exam["problems"][0]["weight"] == 40
    assert exam["problems"][1]["weight"] == 60


def test_create_exam_student_forbidden(student_client, setup_course_and_problems):
    data = setup_course_and_problems

    now = datetime.now(timezone.utc)
    payload = {
        "title": "Unauthorized Exam",
        "duration_minutes": 30,
        "starts_at": now.isoformat(),
        "ends_at": (now + timedelta(hours=1)).isoformat(),
        "problems": [],
    }

    resp = student_client.post(f"/api/v1/courses/{data['course_id']}/exams", json=payload)
    assert resp.status_code == 403


def test_create_exam_invalid_times(instr_client, setup_course_and_problems):
    data = setup_course_and_problems

    now = datetime.now(timezone.utc)
    payload = {
        "title": "Invalid Window Exam",
        "duration_minutes": 30,
        "starts_at": now.isoformat(),
        "ends_at": (now - timedelta(hours=1)).isoformat(),  # ends before starts!
        "problems": [],
    }

    resp = instr_client.post(f"/api/v1/courses/{data['course_id']}/exams", json=payload)
    assert resp.status_code == 400


def test_exam_detail_concealment_and_start_flow(instr_client, student_client, outsider_client, setup_course_and_problems):
    data = setup_course_and_problems

    now = datetime.now(timezone.utc)
    # Create active exam
    payload = {
        "title": "Integrity Lockdown Exam",
        "description": "Lockdown assessment",
        "duration_minutes": 45,
        "starts_at": (now - timedelta(minutes=5)).isoformat(),
        "ends_at": (now + timedelta(hours=2)).isoformat(),
        "is_active": True,
        "fullscreen_required": True,
        "tab_switch_limit": 2,
        "copy_paste_blocked": True,
        "problems": [
            {"problem_id": str(data["p1_id"]), "order_index": 0, "weight": 50},
            {"problem_id": str(data["p2_id"]), "order_index": 1, "weight": 50},
        ],
    }
    create_resp = instr_client.post(f"/api/v1/courses/{data['course_id']}/exams", json=payload)
    assert create_resp.status_code == 201
    exam_id = create_resp.json()["id"]

    # Student retrieves exam before starting session: problems must be concealed
    detail_resp = student_client.get(f"/api/v1/exams/{exam_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["has_session"] is False
    assert detail["problems"][0]["starter_code_python"] is None
    assert "Concealed" in detail["problems"][0]["description"]

    # Student starts exam session
    start_resp = student_client.post(f"/api/v1/exams/{exam_id}/start")
    assert start_resp.status_code == 201
    session_info = start_resp.json()
    session_id = session_info["session_id"]
    assert session_info["remaining_seconds"] > 0
    assert session_info["fullscreen_required"] is True
    # Once session started, problems are revealed
    assert session_info["problems"][0]["starter_code_python"] is not None

    # Resuming session returns the active session
    resume_resp = student_client.post(f"/api/v1/exams/{exam_id}/start")
    assert resume_resp.status_code == 201
    assert resume_resp.json()["session_id"] == session_id

    # Log violations
    v1_resp = student_client.post(
        f"/api/v1/exam-sessions/{session_id}/violations",
        json={"violation_type": "tab_switch", "details": "Switched to browser tab"},
    )
    assert v1_resp.status_code == 201
    v1 = v1_resp.json()
    assert v1["total_violations"] == 1
    assert v1["tab_switches_remaining"] == 1
    assert v1["flagged"] is False

    # Second tab switch reaches limit (2)
    v2_resp = student_client.post(
        f"/api/v1/exam-sessions/{session_id}/violations",
        json={"violation_type": "tab_switch", "details": "Switched again"},
    )
    assert v2_resp.status_code == 201
    v2 = v2_resp.json()
    assert v2["total_violations"] == 2
    assert v2["tab_switches_remaining"] == 0
    assert v2["flagged"] is True

    # Outsider cannot log violation for student's session
    bad_v_resp = outsider_client.post(
        f"/api/v1/exam-sessions/{session_id}/violations",
        json={"violation_type": "focus_loss"},
    )
    assert bad_v_resp.status_code == 403


def test_submit_exam_scoring_and_audit_dashboard(
    instr_client, student2_client, setup_course_and_problems, exam_session_factory
):
    data = setup_course_and_problems

    now = datetime.now(timezone.utc)
    payload = {
        "title": "Graded Final Exam",
        "duration_minutes": 60,
        "starts_at": (now - timedelta(minutes=10)).isoformat(),
        "ends_at": (now + timedelta(hours=2)).isoformat(),
        "is_active": True,
        "problems": [
            {"problem_id": str(data["p1_id"]), "order_index": 0, "weight": 40},
            {"problem_id": str(data["p2_id"]), "order_index": 1, "weight": 60},
        ],
    }
    create_resp = instr_client.post(f"/api/v1/courses/{data['course_id']}/exams", json=payload)
    exam_id = create_resp.json()["id"]

    # Student 2 starts exam
    start_resp = student2_client.post(f"/api/v1/exams/{exam_id}/start")
    assert start_resp.status_code == 201

    # Insert submissions for Student 2
    async def _add_submissions():
        sub_time = datetime.now(timezone.utc) + timedelta(seconds=5)
        async with exam_session_factory() as session:
            # Full solve on Problem 1 (100% -> 40 points)
            session.add(
                Submission(
                    id=uuid.uuid4(),
                    problem_id=data["p1_id"],
                    user_id=_STUDENT2_ID,
                    language="python",
                    source_code="print('hello')",
                    status="accepted",
                    score=100,
                    submitted_at=sub_time,
                )
            )
            # Half solve on Problem 2 (50% -> 30 points)
            session.add(
                Submission(
                    id=uuid.uuid4(),
                    problem_id=data["p2_id"],
                    user_id=_STUDENT2_ID,
                    language="python",
                    source_code="print('half')",
                    status="wrong_answer",
                    score=50,
                    submitted_at=sub_time,
                )
            )
            await session.commit()

    _run_coroutine(_add_submissions())

    # Submit exam
    sub_resp = student2_client.post(f"/api/v1/exams/{exam_id}/submit", json={"is_auto_submitted": False})
    assert sub_resp.status_code == 200
    summary = sub_resp.json()
    assert summary["total_score"] == 70  # 40 + 30
    assert summary["problem_scores"][str(data["p1_id"])] == 40
    assert summary["problem_scores"][str(data["p2_id"])] == 30

    # Student views their own result
    my_res = student2_client.get(f"/api/v1/exams/{exam_id}/my-result")
    assert my_res.status_code == 200
    assert my_res.json()["total_score"] == 70

    # Instructor views audit results dashboard
    dash_resp = instr_client.get(f"/api/v1/exams/{exam_id}/results")
    assert dash_resp.status_code == 200
    dash = dash_resp.json()
    assert dash["total_enrolled"] == 2
    assert dash["submissions_count"] == 1
    assert dash["average_score"] == 70.0
    students_by_id = {s["user_id"]: s for s in dash["students"]}
    assert students_by_id[str(_STUDENT2_ID)]["status"] == "submitted"
    assert students_by_id[str(_STUDENT2_ID)]["total_score"] == 70


def test_exam_update_and_delete(instr_client, setup_course_and_problems):
    data = setup_course_and_problems

    now = datetime.now(timezone.utc)
    create_resp = instr_client.post(
        f"/api/v1/courses/{data['course_id']}/exams",
        json={
            "title": "Temporary Exam",
            "duration_minutes": 30,
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
            "problems": [],
        },
    )
    assert create_resp.status_code == 201
    exam_id = create_resp.json()["id"]

    # Update exam
    up_resp = instr_client.put(
        f"/api/v1/exams/{exam_id}",
        json={"title": "Updated Exam Title", "duration_minutes": 45},
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["title"] == "Updated Exam Title"
    assert up_resp.json()["duration_minutes"] == 45

    # Delete exam
    del_resp = instr_client.delete(f"/api/v1/exams/{exam_id}")
    assert del_resp.status_code == 204

    # Confirm 404
    get_resp = instr_client.get(f"/api/v1/exams/{exam_id}")
    assert get_resp.status_code == 404

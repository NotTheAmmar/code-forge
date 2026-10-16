"""Unit / integration tests for Phase A3: Lab Sessions + Badge Engine.

Uses in-memory SQLite + FastAPI TestClient, authenticated via JWT Bearer tokens.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base
from app.dependencies import get_db
from app.main import app
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lab_session import LabSession, LabSessionProblem
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.test_case import TestCase
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password
from app.services.badge_service import evaluate_badges_async

# ── Database & Fixtures ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture(scope="module")
def instructor_user():
    return User(
        id=uuid.uuid4(),
        email="instructor@labs-test.com",
        name="Prof. Lab Instructor",
        role="instructor",
        password_hash=hash_password("irrelevant"),
    )


@pytest.fixture(scope="module")
def student_user_1():
    return User(
        id=uuid.uuid4(),
        email="student1@labs-test.com",
        name="Alice Student",
        role="student",
        password_hash=hash_password("irrelevant"),
    )


@pytest.fixture(scope="module")
def student_user_2():
    return User(
        id=uuid.uuid4(),
        email="student2@labs-test.com",
        name="Bob Student",
        role="student",
        password_hash=hash_password("irrelevant"),
    )


@pytest.fixture(scope="module", autouse=True)
def create_tables(engine, instructor_user, student_user_1, student_user_2):
    import asyncio
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            session.add_all([instructor_user, student_user_1, student_user_2])
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_create())


@pytest.fixture(scope="module", autouse=True)
def override_db(engine):
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
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


def _make_client(current_user: User) -> TestClient:
    token = create_access_token(str(current_user.id), current_user.role)
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
def instr_client(instructor_user):
    with _make_client(instructor_user) as c:
        yield c


@pytest.fixture
def student1_client(student_user_1):
    with _make_client(student_user_1) as c:
        yield c


@pytest.fixture
def student2_client(student_user_2):
    with _make_client(student_user_2) as c:
        yield c


# ── Shared Course and Problems Fixture ────────────────────────────────────────

@pytest.fixture
def lab_setup(instr_client, student1_client, student2_client):
    """Sets up a course with 3 problems, enrolls 2 students."""
    # 1. Create course
    course_resp = instr_client.post("/api/v1/courses", json={"title": "Lab Course 101"})
    assert course_resp.status_code == 201
    course = course_resp.json()
    course_id = course["id"]
    invite_code = course["invite_code"]

    # 2. Join students
    s1_join = student1_client.post(f"/api/v1/courses/{course_id}/join", json={"invite_code": invite_code})
    assert s1_join.status_code == 201
    s2_join = student2_client.post(f"/api/v1/courses/{course_id}/join", json={"invite_code": invite_code})
    assert s2_join.status_code == 201

    # 3. Create 3 problems
    problems = []
    for i in range(1, 4):
        slug = f"lab-prob-{i}-{uuid.uuid4().hex[:6]}"
        p_resp = instr_client.post(
            f"/api/v1/courses/{course_id}/problems",
            json={
                "slug": slug,
                "title": f"Problem {i}",
                "description": f"Description for problem {i}",
                "difficulty": "easy",
                "starter_code_java": "class Solution {}",
                "test_cases": [
                    {"label": "01", "input_data": "1", "expected_output": "1", "is_visible": True, "order_index": 0}
                ],
            },
        )
        assert p_resp.status_code == 201
        problems.append(p_resp.json())

    return {
        "course": course,
        "problems": problems,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Lab Session CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateLabSession:
    def test_instructor_can_create_lab(self, instr_client, lab_setup):
        course_id = lab_setup["course"]["id"]
        prob_ids = [p["id"] for p in lab_setup["problems"]]

        resp = instr_client.post(
            f"/api/v1/courses/{course_id}/labs",
            json={
                "title": "Lab 1 - Pointers",
                "description": "Pointer arithmetic exercises",
                "mandatory_count": 1,
                "problem_ids": prob_ids,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Lab 1 - Pointers"
        assert data["mandatory_count"] == 1
        assert data["problem_count"] == 3
        assert data["is_active"] is True

    def test_student_cannot_create_lab(self, student1_client, lab_setup):
        course_id = lab_setup["course"]["id"]
        resp = student1_client.post(
            f"/api/v1/courses/{course_id}/labs",
            json={"title": "Hacked Lab", "problem_ids": []},
        )
        assert resp.status_code == 403

    def test_invalid_problem_id_rejected(self, instr_client, lab_setup):
        course_id = lab_setup["course"]["id"]
        resp = instr_client.post(
            f"/api/v1/courses/{course_id}/labs",
            json={
                "title": "Invalid Lab",
                "problem_ids": [str(uuid.uuid4())],
            },
        )
        assert resp.status_code == 400


class TestListCourseLabs:
    def test_enrolled_users_can_list_labs(self, instr_client, student1_client, lab_setup):
        course_id = lab_setup["course"]["id"]
        # Create a lab
        instr_client.post(
            f"/api/v1/courses/{course_id}/labs",
            json={"title": "List Lab Test", "problem_ids": [lab_setup["problems"][0]["id"]]},
        )

        resp = student1_client.get(f"/api/v1/courses/{course_id}/labs")
        assert resp.status_code == 200
        labs = resp.json()
        assert isinstance(labs, list)
        assert any(l["title"] == "List Lab Test" for l in labs)


class TestGetAndUpdateLab:
    def test_get_lab_detail(self, instr_client, student1_client, lab_setup):
        course_id = lab_setup["course"]["id"]
        prob_ids = [p["id"] for p in lab_setup["problems"][:2]]
        create_resp = instr_client.post(
            f"/api/v1/courses/{course_id}/labs",
            json={"title": "Detail Lab", "problem_ids": prob_ids},
        )
        lab_id = create_resp.json()["id"]

        resp = student1_client.get(f"/api/v1/labs/{lab_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == lab_id
        assert len(data["problems"]) == 2
        assert data["problems"][0]["id"] == prob_ids[0]

    def test_update_lab_session(self, instr_client, lab_setup):
        course_id = lab_setup["course"]["id"]
        create_resp = instr_client.post(
            f"/api/v1/courses/{course_id}/labs",
            json={"title": "Old Lab Title", "mandatory_count": 1, "problem_ids": []},
        )
        lab_id = create_resp.json()["id"]

        # Update title and mandatory_count
        resp = instr_client.put(
            f"/api/v1/labs/{lab_id}",
            json={
                "title": "Updated Lab Title",
                "mandatory_count": 2,
                "problem_ids": [lab_setup["problems"][0]["id"]],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated Lab Title"
        assert data["mandatory_count"] == 2
        assert len(data["problems"]) == 1

    def test_student_cannot_update_lab(self, student1_client, instr_client, lab_setup):
        course_id = lab_setup["course"]["id"]
        create_resp = instr_client.post(
            f"/api/v1/courses/{course_id}/labs",
            json={"title": "Protected Lab", "problem_ids": []},
        )
        lab_id = create_resp.json()["id"]

        resp = student1_client.put(
            f"/api/v1/labs/{lab_id}",
            json={"title": "Student Updated"},
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Badge Engine & Submission Flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestBadgeEngineAndSubmissions:
    @pytest.mark.asyncio
    async def test_badge_award_logic(self, engine, instructor_user, student_user_1, lab_setup):
        """Simulate submissions and verify badge logic directly."""
        course_id = uuid.UUID(lab_setup["course"]["id"])
        prob1_id = uuid.UUID(lab_setup["problems"][0]["id"])
        prob2_id = uuid.UUID(lab_setup["problems"][1]["id"])
        prob3_id = uuid.UUID(lab_setup["problems"][2]["id"])

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        lab_id = uuid.uuid4()

        async with session_factory() as session:
            # Create a lab with mandatory_count = 1
            lab = LabSession(
                id=lab_id,
                course_id=course_id,
                title="Badge Test Lab",
                mandatory_count=1,
                is_active=True,
            )
            session.add(lab)
            await session.flush()

            for idx, pid in enumerate([prob1_id, prob2_id, prob3_id]):
                session.add(LabSessionProblem(lab_session_id=lab.id, problem_id=pid, order_index=idx))
            await session.commit()

        # Step 1: Student 1 solves problem 1 (count = 1 == mandatory_count) -> NO badge
        async with session_factory() as session:
            sub1 = Submission(
                id=uuid.uuid4(),
                problem_id=prob1_id,
                user_id=student_user_1.id,
                lab_session_id=lab_id,
                is_full_submit=True,
                status="completed",
                score=100,
                total_cases=1,
                passed_cases=1,
                source_code="...",
            )
            session.add(sub1)
            await session.commit()

            b1 = await evaluate_badges_async(session, sub1)
            assert b1 is None  # count == 1, not > mandatory (1)

        # Step 2: Student 1 solves problem 2 (count = 2 > mandatory_count) -> BADGE awarded!
        async with session_factory() as session:
            sub2 = Submission(
                id=uuid.uuid4(),
                problem_id=prob2_id,
                user_id=student_user_1.id,
                lab_session_id=lab_id,
                is_full_submit=True,
                status="completed",
                score=100,
                total_cases=1,
                passed_cases=1,
                source_code="...",
            )
            session.add(sub2)
            await session.commit()

            b2 = await evaluate_badges_async(session, sub2)
            assert b2 is not None
            assert b2.problem_id == prob2_id
            assert b2.user_id == student_user_1.id

        # Step 3: Student 1 submits problem 2 again (duplicate solve) -> NO duplicate badge
        async with session_factory() as session:
            sub2_dup = Submission(
                id=uuid.uuid4(),
                problem_id=prob2_id,
                user_id=student_user_1.id,
                lab_session_id=lab_id,
                is_full_submit=True,
                status="completed",
                score=100,
                total_cases=1,
                passed_cases=1,
                source_code="...",
            )
            session.add(sub2_dup)
            await session.commit()

            b2_dup = await evaluate_badges_async(session, sub2_dup)
            assert b2_dup is None

        # Step 4: Student 1 solves problem 3 (count = 3 > mandatory_count) -> BADGE awarded!
        async with session_factory() as session:
            sub3 = Submission(
                id=uuid.uuid4(),
                problem_id=prob3_id,
                user_id=student_user_1.id,
                lab_session_id=lab_id,
                is_full_submit=True,
                status="completed",
                score=100,
                total_cases=1,
                passed_cases=1,
                source_code="...",
            )
            session.add(sub3)
            await session.commit()

            b3 = await evaluate_badges_async(session, sub3)
            assert b3 is not None
            assert b3.problem_id == prob3_id

    def test_submission_endpoint_tags_active_lab(self, instr_client, student1_client, lab_setup):
        """When submitting code, the active lab session is automatically tagged."""
        course_id = lab_setup["course"]["id"]
        prob = lab_setup["problems"][0]

        # Create active lab containing problem 0
        lab_resp = instr_client.post(
            f"/api/v1/courses/{course_id}/labs",
            json={"title": "Active Lab Tagging", "problem_ids": [prob["id"]]},
        )
        lab_id = lab_resp.json()["id"]

        from unittest.mock import patch
        with patch("app.worker.tasks.grade_submission.delay"):
            sub_resp = student1_client.post(
                f"/api/v1/problems/{prob['slug']}/submit",
                json={"source_code": "class Solution {}", "language": "java"},
            )
            assert sub_resp.status_code == 202
            sub_id = sub_resp.json()["submission_id"]

        # Check submission details
        get_sub = student1_client.get(f"/api/v1/submissions/{sub_id}")
        assert get_sub.status_code == 200
        assert get_sub.json()["lab_session_id"] == lab_id


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard and Student Progress
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardAndProgress:
    @pytest.mark.asyncio
    async def test_dashboard_and_progress_flow(
        self, engine, instr_client, student1_client, student2_client, student_user_1, student_user_2, lab_setup
    ):
        course_id = uuid.UUID(lab_setup["course"]["id"])
        prob1_id = uuid.UUID(lab_setup["problems"][0]["id"])
        prob2_id = uuid.UUID(lab_setup["problems"][1]["id"])
        lab_id = uuid.uuid4()

        # Create lab
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            lab = LabSession(
                id=lab_id,
                course_id=course_id,
                title="Dashboard Test Lab",
                mandatory_count=1,
                is_active=True,
            )
            session.add(lab)
            await session.flush()
            session.add(LabSessionProblem(lab_session_id=lab.id, problem_id=prob1_id, order_index=0))
            session.add(LabSessionProblem(lab_session_id=lab.id, problem_id=prob2_id, order_index=1))

            # Student 1 solves problem 1 (mandatory -> 0 badges)
            s1_sub1 = Submission(
                id=uuid.uuid4(),
                problem_id=prob1_id,
                user_id=student_user_1.id,
                lab_session_id=lab_id,
                is_full_submit=True,
                status="completed",
                score=100,
                total_cases=1,
                passed_cases=1,
                source_code="...",
            )
            session.add(s1_sub1)
            await session.commit()
            await evaluate_badges_async(session, s1_sub1)

            # Student 1 solves problem 2 (extra -> 1st badge)
            s1_sub2 = Submission(
                id=uuid.uuid4(),
                problem_id=prob2_id,
                user_id=student_user_1.id,
                lab_session_id=lab_id,
                is_full_submit=True,
                status="completed",
                score=100,
                total_cases=1,
                passed_cases=1,
                source_code="...",
            )
            session.add(s1_sub2)
            await session.commit()
            await evaluate_badges_async(session, s1_sub2)

            # Student 2 solves only problem 1 (mandatory completed, 0 badges)
            s2_sub1 = Submission(
                id=uuid.uuid4(),
                problem_id=prob1_id,
                user_id=student_user_2.id,
                lab_session_id=lab_id,
                is_full_submit=True,
                status="completed",
                score=100,
                total_cases=1,
                passed_cases=1,
                source_code="...",
            )
            session.add(s2_sub1)
            await session.commit()
            await evaluate_badges_async(session, s2_sub1)

        # 1. Test Instructor Dashboard
        dash_resp = instr_client.get(f"/api/v1/labs/{lab_id}/dashboard")
        assert dash_resp.status_code == 200
        dash = dash_resp.json()
        assert dash["total_students"] >= 2
        assert dash["total_badges_awarded"] == 1
        assert dash["mandatory_count"] == 1

        # Student 1 should be first because badge_count == 1
        students = dash["students"]
        s1_row = next(s for s in students if s["user_id"] == str(student_user_1.id))
        s2_row = next(s for s in students if s["user_id"] == str(student_user_2.id))

        assert s1_row["problems_solved"] == 2
        assert s1_row["mandatory_completed"] is True
        assert s1_row["badge_count"] == 1
        assert s1_row["last_submission_at"] is not None

        assert s2_row["problems_solved"] == 1
        assert s2_row["mandatory_completed"] is True
        assert s2_row["badge_count"] == 0

        # Check sorting: s1 before s2
        assert students.index(s1_row) < students.index(s2_row)

        # Student cannot view dashboard
        assert student1_client.get(f"/api/v1/labs/{lab_id}/dashboard").status_code == 403

        # 2. Test Student Progress Endpoint
        prog1_resp = student1_client.get(f"/api/v1/labs/{lab_id}/my-progress")
        assert prog1_resp.status_code == 200
        prog1 = prog1_resp.json()
        assert prog1["problems_solved_count"] == 2
        assert prog1["mandatory_completed"] is True
        assert prog1["badge_count"] == 1
        assert prog1["recent_badge_earned"] is not None
        assert prog1["recent_badge_earned"]["problem_id"] == str(prob2_id)

        prog2_resp = student2_client.get(f"/api/v1/labs/{lab_id}/my-progress")
        assert prog2_resp.status_code == 200
        prog2 = prog2_resp.json()
        assert prog2["problems_solved_count"] == 1
        assert prog2["mandatory_completed"] is True
        assert prog2["badge_count"] == 0
        assert prog2["recent_badge_earned"] is None

"""Tests for Submission History API (GET /problems/{id_or_slug}/submissions)
and Submission Access Control (GET /submissions/{id}).
"""

import uuid
from datetime import datetime, timezone, timedelta
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
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password


@pytest.fixture(scope="module")
def history_engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture(scope="module", autouse=True)
def setup_history_db(history_engine):
    import asyncio

    async def _init():
        async with history_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_init())
    yield
    asyncio.get_event_loop().run_until_complete(history_engine.dispose())


@pytest.fixture
def history_session_factory(history_engine):
    return async_sessionmaker(history_engine, expire_on_commit=False)


@pytest.fixture
def make_client(history_session_factory):
    def _factory(user: User | None = None) -> TestClient:
        async def _override_get_db():
            async with history_session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_db] = _override_get_db
        client = TestClient(app)
        if user is not None:
            token = create_access_token(user_id=str(user.id), role=user.role)
            client.headers["Authorization"] = f"Bearer {token}"
        return client

    return _factory


@pytest.fixture
async def seeded_data(history_session_factory):
    """Seed instructor, two students, course, and a problem."""
    async with history_session_factory() as session:
        instructor = User(
            id=uuid.uuid4(),
            email=f"inst_{uuid.uuid4().hex[:6]}@univ.edu",
            name="Prof Hist",
            role="instructor",
            password_hash=hash_password("password123"),
        )
        student1 = User(
            id=uuid.uuid4(),
            email=f"s1_{uuid.uuid4().hex[:6]}@univ.edu",
            name="Student One",
            role="student",
            password_hash=hash_password("password123"),
        )
        student2 = User(
            id=uuid.uuid4(),
            email=f"s2_{uuid.uuid4().hex[:6]}@univ.edu",
            name="Student Two",
            role="student",
            password_hash=hash_password("password123"),
        )
        course = Course(
            id=uuid.uuid4(),
            title="CS101 History Test",
            created_by=instructor.id,
            invite_code=uuid.uuid4().hex[:6].upper(),
        )
        enr_inst = Enrollment(id=uuid.uuid4(), user_id=instructor.id, course_id=course.id, role="instructor")
        enr_s1 = Enrollment(id=uuid.uuid4(), user_id=student1.id, course_id=course.id, role="student")
        enr_s2 = Enrollment(id=uuid.uuid4(), user_id=student2.id, course_id=course.id, role="student")

        slug = f"prob-hist-{uuid.uuid4().hex[:8]}"
        problem = Problem(
            id=uuid.uuid4(),
            course_id=course.id,
            created_by=instructor.id,
            slug=slug,
            title="Problem for History",
            description="Test problem description",
            difficulty="easy",
            starter_code_java="class Solution {}",
            starter_code_python="print('test')",
        )

        session.add_all([instructor, student1, student2, course, enr_inst, enr_s1, enr_s2, problem])
        await session.commit()

        return {
            "instructor": instructor,
            "student1": student1,
            "student2": student2,
            "course": course,
            "problem": problem,
        }


# ── Submission History Tests ──────────────────────────────────────────────────

class TestSubmissionHistory:
    @pytest.mark.asyncio
    async def test_history_empty_for_new_problem(self, seeded_data, make_client):
        data = seeded_data
        client = make_client(data["student1"])
        slug = data["problem"].slug

        res = client.get(f"/api/v1/problems/{slug}/submissions")
        assert res.status_code == 200
        assert res.json() == []

    @pytest.mark.asyncio
    async def test_history_404_nonexistent_problem(self, seeded_data, make_client):
        data = seeded_data
        client = make_client(data["student1"])

        res = client.get("/api/v1/problems/nonexistent-prob-12345/submissions")
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_history_by_slug_and_uuid(self, seeded_data, make_client, history_session_factory):
        data = seeded_data
        s1 = data["student1"]
        prob = data["problem"]

        # Insert a submission for student1
        async with history_session_factory() as session:
            sub = Submission(
                id=uuid.uuid4(),
                problem_id=prob.id,
                user_id=s1.id,
                language="python",
                source_code="print('hi')",
                status="completed",
                is_full_submit=True,
                score=100,
                total_cases=2,
                passed_cases=2,
            )
            session.add(sub)
            await session.commit()

        client = make_client(s1)

        # Query by slug
        res_slug = client.get(f"/api/v1/problems/{prob.slug}/submissions")
        assert res_slug.status_code == 200
        items_slug = res_slug.json()
        assert len(items_slug) == 1
        assert items_slug[0]["language"] == "python"
        assert items_slug[0]["score"] == 100
        assert items_slug[0]["is_best"] is True

        # Query by UUID
        res_uuid = client.get(f"/api/v1/problems/{prob.id}/submissions")
        assert res_uuid.status_code == 200
        items_uuid = res_uuid.json()
        assert len(items_uuid) == 1
        assert items_uuid[0]["id"] == items_slug[0]["id"]

    @pytest.mark.asyncio
    async def test_history_ordering_and_is_best(self, seeded_data, make_client, history_session_factory):
        data = seeded_data
        s1 = data["student1"]
        prob = data["problem"]

        base_time = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)

        # Submissions:
        # Sub 1: score 70 at T1
        # Sub 2: score 100 at T2 (earliest 100 -> should be is_best)
        # Sub 3: score 100 at T3 (later 100 -> tied, so earlier wins)
        sub1_id = uuid.uuid4()
        sub2_id = uuid.uuid4()
        sub3_id = uuid.uuid4()

        async with history_session_factory() as session:
            s1_sub = Submission(
                id=sub1_id,
                problem_id=prob.id,
                user_id=s1.id,
                language="java",
                source_code="// v1",
                status="completed",
                is_full_submit=True,
                score=70,
                passed_cases=7,
                total_cases=10,
                submitted_at=base_time,
            )
            s2_sub = Submission(
                id=sub2_id,
                problem_id=prob.id,
                user_id=s1.id,
                language="python",
                source_code="# v2",
                status="completed",
                is_full_submit=True,
                score=100,
                passed_cases=10,
                total_cases=10,
                submitted_at=base_time + timedelta(minutes=15),
            )
            s3_sub = Submission(
                id=sub3_id,
                problem_id=prob.id,
                user_id=s1.id,
                language="python",
                source_code="# v3",
                status="completed",
                is_full_submit=True,
                score=100,
                passed_cases=10,
                total_cases=10,
                submitted_at=base_time + timedelta(minutes=30),
            )
            session.add_all([s1_sub, s2_sub, s3_sub])
            await session.commit()

        client = make_client(s1)
        res = client.get(f"/api/v1/problems/{prob.slug}/submissions")
        assert res.status_code == 200
        items = res.json()
        assert len(items) >= 3

        # Must be ordered by submitted_at DESC
        # First item should be sub3 (at T3)
        assert items[0]["id"] == str(sub3_id)
        assert items[0]["score"] == 100
        assert items[0]["is_best"] is False  # Tied, but sub2 was earlier

        # Second item should be sub2 (at T2)
        assert items[1]["id"] == str(sub2_id)
        assert items[1]["score"] == 100
        assert items[1]["is_best"] is True   # Earlier 100 is best

        # Third item should be sub1 (at T1)
        assert items[2]["id"] == str(sub1_id)
        assert items[2]["score"] == 70
        assert items[2]["is_best"] is False

    @pytest.mark.asyncio
    async def test_history_user_isolation(self, seeded_data, make_client, history_session_factory):
        data = seeded_data
        s2 = data["student2"]
        prob = data["problem"]

        # Student2 has not made any submissions; student1 has
        client2 = make_client(s2)
        res = client2.get(f"/api/v1/problems/{prob.slug}/submissions")
        assert res.status_code == 200
        assert res.json() == []


# ── Submission Access Control Tests ───────────────────────────────────────────

class TestSubmissionAccessControl:
    @pytest.mark.asyncio
    async def test_student_can_view_own_submission(self, seeded_data, make_client, history_session_factory):
        data = seeded_data
        s1 = data["student1"]
        prob = data["problem"]

        sub_id = uuid.uuid4()
        async with history_session_factory() as session:
            sub = Submission(
                id=sub_id,
                problem_id=prob.id,
                user_id=s1.id,
                language="python",
                source_code="print('access test')",
                status="completed",
                score=100,
            )
            session.add(sub)
            await session.commit()

        client1 = make_client(s1)
        res = client1.get(f"/api/v1/submissions/{sub_id}")
        assert res.status_code == 200
        assert res.json()["id"] == str(sub_id)

    @pytest.mark.asyncio
    async def test_instructor_can_view_any_submission(self, seeded_data, make_client, history_session_factory):
        data = seeded_data
        s1 = data["student1"]
        inst = data["instructor"]
        prob = data["problem"]

        sub_id = uuid.uuid4()
        async with history_session_factory() as session:
            sub = Submission(
                id=sub_id,
                problem_id=prob.id,
                user_id=s1.id,
                language="java",
                source_code="class Sol {}",
                status="completed",
                score=80,
            )
            session.add(sub)
            await session.commit()

        inst_client = make_client(inst)
        res = inst_client.get(f"/api/v1/submissions/{sub_id}")
        assert res.status_code == 200
        assert res.json()["id"] == str(sub_id)

    @pytest.mark.asyncio
    async def test_unrelated_student_gets_403(self, seeded_data, make_client, history_session_factory):
        data = seeded_data
        s1 = data["student1"]
        s2 = data["student2"]
        prob = data["problem"]

        sub_id = uuid.uuid4()
        async with history_session_factory() as session:
            sub = Submission(
                id=sub_id,
                problem_id=prob.id,
                user_id=s1.id,
                language="python",
                source_code="secret code",
                status="completed",
            )
            session.add(sub)
            await session.commit()

        client2 = make_client(s2)
        res = client2.get(f"/api/v1/submissions/{sub_id}")
        assert res.status_code == 403
        assert "permission" in res.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(self, seeded_data, make_client):
        unauth_client = make_client(None)
        res = unauth_client.get(f"/api/v1/submissions/{uuid.uuid4()}")
        assert res.status_code in (401, 403)

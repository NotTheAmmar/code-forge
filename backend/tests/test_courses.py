"""Unit / integration tests for Phase A2: Course system + Problem CRUD API.

Uses in-memory SQLite + FastAPI TestClient, same pattern as test_auth.py.
All auth-required endpoints use dependency overrides to inject a pre-built
instructor or student User.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.dependencies import get_db, get_current_user
from app.main import app
from app.models.user import User
from app.services.auth_service import hash_password

# ── Shared async SQLite engine ────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture(scope="module", autouse=True)
def create_tables(engine):
    import asyncio

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_create())


# ── Reusable fixture factory ──────────────────────────────────────────────────

def _make_client(engine, current_user: User) -> TestClient:
    """Return a TestClient with get_db and get_current_user overridden."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_current_user():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


def _clear_overrides():
    app.dependency_overrides.clear()


# ── Pre-built users ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def instructor_user():
    return User(
        id=uuid.uuid4(),
        email="instructor@courses-test.com",
        name="Instructor",
        role="instructor",
        password_hash=hash_password("irrelevant"),
    )


@pytest.fixture(scope="module")
def student_user():
    return User(
        id=uuid.uuid4(),
        email="student@courses-test.com",
        name="Student",
        role="student",
        password_hash=hash_password("irrelevant"),
    )


@pytest.fixture
def instr_client(engine, instructor_user):
    client = _make_client(engine, instructor_user)
    with client:
        yield client
    _clear_overrides()


@pytest.fixture
def student_client(engine, student_user):
    client = _make_client(engine, student_user)
    with client:
        yield client
    _clear_overrides()


# ═══════════════════════════════════════════════════════════════════════════════
# Course CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateCourse:
    def test_instructor_can_create_course(self, instr_client):
        resp = instr_client.post("/api/v1/courses", json={
            "title": "Data Structures",
            "description": "Stacks, queues, trees, graphs",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Data Structures"
        assert len(data["invite_code"]) == 6
        assert data["role"] == "instructor"
        assert data["member_count"] == 1  # creator auto-enrolled

    def test_student_cannot_create_course(self, student_client):
        resp = student_client.post("/api/v1/courses", json={"title": "Nope"})
        assert resp.status_code == 403

    def test_missing_title_rejected(self, instr_client):
        resp = instr_client.post("/api/v1/courses", json={"description": "no title"})
        assert resp.status_code == 422


class TestListCourses:
    def test_returns_enrolled_courses(self, instr_client):
        # Create a course first
        instr_client.post("/api/v1/courses", json={"title": "List Test Course"})
        resp = instr_client.get("/api/v1/courses")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        titles = [c["title"] for c in resp.json()]
        assert "List Test Course" in titles

    def test_student_with_no_courses_returns_empty(self, student_client):
        resp = student_client.get("/api/v1/courses")
        assert resp.status_code == 200
        # Student hasn't joined anything yet
        assert isinstance(resp.json(), list)


class TestJoinCourse:
    def _create_course(self, instr_client) -> dict:
        resp = instr_client.post("/api/v1/courses", json={"title": "Join Test"})
        assert resp.status_code == 201
        return resp.json()

    def test_student_can_join_with_correct_code(self, instr_client, student_client):
        course = self._create_course(instr_client)
        resp = student_client.post(
            f"/api/v1/courses/{course['id']}/join",
            json={"invite_code": course["invite_code"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["role"] == "student"
        assert data["course_id"] == course["id"]

    def test_wrong_code_returns_400(self, instr_client, student_client):
        course = self._create_course(instr_client)
        resp = student_client.post(
            f"/api/v1/courses/{course['id']}/join",
            json={"invite_code": "XXXXXX"},
        )
        assert resp.status_code == 400

    def test_duplicate_join_returns_409(self, instr_client, student_client):
        course = self._create_course(instr_client)
        student_client.post(
            f"/api/v1/courses/{course['id']}/join",
            json={"invite_code": course["invite_code"]},
        )
        # Second join
        resp = student_client.post(
            f"/api/v1/courses/{course['id']}/join",
            json={"invite_code": course["invite_code"]},
        )
        assert resp.status_code == 409


class TestGetCourseDetail:
    def test_instructor_can_see_course(self, instr_client):
        create = instr_client.post("/api/v1/courses", json={"title": "Detail Course"})
        course_id = create.json()["id"]
        resp = instr_client.get(f"/api/v1/courses/{course_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Detail Course"

    def test_unenrolled_student_gets_403(self, engine, student_user, instr_client):
        create = instr_client.post("/api/v1/courses", json={"title": "Private Course"})
        course_id = create.json()["id"]

        # Fresh student not enrolled in this course
        other_student = User(
            id=uuid.uuid4(),
            email="other@courses-test.com",
            name="Other",
            role="student",
            password_hash="x",
        )
        client = _make_client(engine, other_student)
        with client:
            resp = client.get(f"/api/v1/courses/{course_id}")
        _clear_overrides()
        assert resp.status_code == 403

    def test_nonexistent_course_returns_404(self, instr_client):
        resp = instr_client.get(f"/api/v1/courses/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestListMembers:
    def test_instructor_can_list_members(self, instr_client, student_client):
        course = instr_client.post("/api/v1/courses", json={"title": "Members Course"}).json()
        student_client.post(
            f"/api/v1/courses/{course['id']}/join",
            json={"invite_code": course["invite_code"]},
        )
        resp = instr_client.get(f"/api/v1/courses/{course['id']}/members")
        assert resp.status_code == 200
        members = resp.json()
        roles = {m["role"] for m in members}
        assert "instructor" in roles
        assert "student" in roles

    def test_student_cannot_list_members(self, instr_client, student_client):
        course = instr_client.post("/api/v1/courses", json={"title": "Members Forbidden"}).json()
        student_client.post(
            f"/api/v1/courses/{course['id']}/join",
            json={"invite_code": course["invite_code"]},
        )
        resp = student_client.get(f"/api/v1/courses/{course['id']}/members")
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Problem CRUD
# ═══════════════════════════════════════════════════════════════════════════════

_PROBLEM_BODY = {
    "slug": "two-sum",
    "title": "Two Sum",
    "description": "Find two numbers that add up to target.",
    "difficulty": "easy",
    "starter_code_java": "class Solution {}",
    "time_limit_sec": 5,
    "memory_limit_mb": 128,
    "test_cases": [
        {"label": "01", "input_data": "2 7 11 15\n9", "expected_output": "0 1", "is_visible": True, "order_index": 0},
        {"label": "02", "input_data": "3 2 4\n6", "expected_output": "1 2", "is_visible": False, "order_index": 1},
    ],
}


class TestCreateProblem:
    def _create_course(self, instr_client) -> str:
        return instr_client.post("/api/v1/courses", json={"title": "Prob Course"}).json()["id"]

    def test_instructor_creates_problem(self, instr_client):
        course_id = self._create_course(instr_client)
        body = dict(_PROBLEM_BODY, slug=f"two-sum-{uuid.uuid4().hex[:6]}")
        resp = instr_client.post(f"/api/v1/courses/{course_id}/problems", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Two Sum"
        assert len(data["test_cases"]) == 2

    def test_duplicate_slug_returns_409(self, instr_client):
        course_id = self._create_course(instr_client)
        slug = f"dup-slug-{uuid.uuid4().hex[:6]}"
        body = dict(_PROBLEM_BODY, slug=slug)
        instr_client.post(f"/api/v1/courses/{course_id}/problems", json=body)
        resp = instr_client.post(f"/api/v1/courses/{course_id}/problems", json=body)
        assert resp.status_code == 409

    def test_student_cannot_create_problem(self, instr_client, student_client):
        course = instr_client.post("/api/v1/courses", json={"title": "Perm Check"}).json()
        student_client.post(
            f"/api/v1/courses/{course['id']}/join",
            json={"invite_code": course["invite_code"]},
        )
        body = dict(_PROBLEM_BODY, slug=f"student-attempt-{uuid.uuid4().hex[:6]}")
        resp = student_client.post(f"/api/v1/courses/{course['id']}/problems", json=body)
        assert resp.status_code == 403


class TestListAndGetProblems:
    def _setup(self, instr_client) -> tuple[str, dict]:
        course_id = instr_client.post("/api/v1/courses", json={"title": "List Probs"}).json()["id"]
        slug = f"list-prob-{uuid.uuid4().hex[:6]}"
        prob = instr_client.post(
            f"/api/v1/courses/{course_id}/problems",
            json=dict(_PROBLEM_BODY, slug=slug),
        ).json()
        return course_id, prob

    def test_list_problems_in_course(self, instr_client):
        course_id, prob = self._setup(instr_client)
        resp = instr_client.get(f"/api/v1/courses/{course_id}/problems")
        assert resp.status_code == 200
        slugs = [p["slug"] for p in resp.json()]
        assert prob["slug"] in slugs

    def test_get_problem_detail(self, instr_client):
        course_id, prob = self._setup(instr_client)
        resp = instr_client.get(f"/api/v1/courses/{course_id}/problems/{prob['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == prob["id"]
        assert len(resp.json()["test_cases"]) == 2

    def test_get_problem_wrong_course_returns_404(self, instr_client):
        _, prob = self._setup(instr_client)
        other_course_id = instr_client.post("/api/v1/courses", json={"title": "Other"}).json()["id"]
        resp = instr_client.get(f"/api/v1/courses/{other_course_id}/problems/{prob['id']}")
        assert resp.status_code == 404


class TestUpdateProblem:
    def _create_problem(self, instr_client) -> tuple[str, dict]:
        course_id = instr_client.post("/api/v1/courses", json={"title": "Update Course"}).json()["id"]
        slug = f"update-prob-{uuid.uuid4().hex[:6]}"
        prob = instr_client.post(
            f"/api/v1/courses/{course_id}/problems",
            json=dict(_PROBLEM_BODY, slug=slug),
        ).json()
        return course_id, prob

    def test_update_title(self, instr_client):
        _, prob = self._create_problem(instr_client)
        resp = instr_client.put(f"/api/v1/problems/{prob['id']}", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_update_replaces_test_cases(self, instr_client):
        _, prob = self._create_problem(instr_client)
        new_cases = [{"label": "99", "input_data": "x", "expected_output": "y", "is_visible": True, "order_index": 0}]
        resp = instr_client.put(f"/api/v1/problems/{prob['id']}", json={"test_cases": new_cases})
        assert resp.status_code == 200
        assert len(resp.json()["test_cases"]) == 1
        assert resp.json()["test_cases"][0]["label"] == "99"

    def test_update_nonexistent_problem_returns_404(self, instr_client):
        resp = instr_client.put(f"/api/v1/problems/{uuid.uuid4()}", json={"title": "ghost"})
        assert resp.status_code == 404


class TestDeleteProblem:
    def _create_problem(self, instr_client) -> dict:
        course_id = instr_client.post("/api/v1/courses", json={"title": "Del Course"}).json()["id"]
        slug = f"del-prob-{uuid.uuid4().hex[:6]}"
        return instr_client.post(
            f"/api/v1/courses/{course_id}/problems",
            json=dict(_PROBLEM_BODY, slug=slug),
        ).json()

    def test_delete_problem(self, instr_client):
        prob = self._create_problem(instr_client)
        resp = instr_client.delete(f"/api/v1/problems/{prob['id']}")
        assert resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, instr_client):
        resp = instr_client.delete(f"/api/v1/problems/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestBulkImport:
    def _course_id(self, instr_client) -> str:
        return instr_client.post("/api/v1/courses", json={"title": "Bulk Course"}).json()["id"]

    def test_bulk_import_success(self, instr_client):
        course_id = self._course_id(instr_client)
        problems = [
            dict(_PROBLEM_BODY, slug=f"bulk-a-{uuid.uuid4().hex[:6]}"),
            dict(_PROBLEM_BODY, slug=f"bulk-b-{uuid.uuid4().hex[:6]}"),
        ]
        resp = instr_client.post(
            f"/api/v1/courses/{course_id}/problems/bulk-import",
            json={"problems": problems},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["imported_count"] == 2
        assert data["failed_count"] == 0

    def test_bulk_import_partial_failure(self, instr_client):
        course_id = self._course_id(instr_client)
        unique_slug = f"bulk-unique-{uuid.uuid4().hex[:6]}"
        # First insert the unique slug
        instr_client.post(
            f"/api/v1/courses/{course_id}/problems",
            json=dict(_PROBLEM_BODY, slug=unique_slug),
        )
        # Now bulk import with the duplicate slug + a new one
        new_slug = f"bulk-new-{uuid.uuid4().hex[:6]}"
        resp = instr_client.post(
            f"/api/v1/courses/{course_id}/problems/bulk-import",
            json={"problems": [
                dict(_PROBLEM_BODY, slug=unique_slug),   # will fail (dup)
                dict(_PROBLEM_BODY, slug=new_slug),      # should succeed
            ]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["failed_count"] == 1
        assert data["imported_count"] == 1
        assert new_slug in data["imported_slugs"]
        assert len(data["errors"]) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Gradebook
# ═══════════════════════════════════════════════════════════════════════════════

class TestGradebook:
    def test_empty_gradebook(self, instr_client):
        course_id = instr_client.post("/api/v1/courses", json={"title": "GB Empty"}).json()["id"]
        resp = instr_client.get(f"/api/v1/courses/{course_id}/gradebook")
        assert resp.status_code == 200
        data = resp.json()
        assert "problems" in data
        assert "rows" in data
        assert data["rows"] == []

    def test_gradebook_structure_with_problem(self, instr_client):
        course_id = instr_client.post("/api/v1/courses", json={"title": "GB With Prob"}).json()["id"]
        instr_client.post(
            f"/api/v1/courses/{course_id}/problems",
            json=dict(_PROBLEM_BODY, slug=f"gb-prob-{uuid.uuid4().hex[:6]}"),
        )
        resp = instr_client.get(f"/api/v1/courses/{course_id}/gradebook")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["problems"]) == 1
        assert "slug" in data["problems"][0]
        assert "title" in data["problems"][0]

    def test_student_cannot_view_gradebook(self, instr_client, student_client):
        course = instr_client.post("/api/v1/courses", json={"title": "GB Perm"}).json()
        student_client.post(
            f"/api/v1/courses/{course['id']}/join",
            json={"invite_code": course["invite_code"]},
        )
        resp = student_client.get(f"/api/v1/courses/{course['id']}/gradebook")
        assert resp.status_code == 403

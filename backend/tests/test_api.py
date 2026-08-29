"""Integration tests for API endpoints.

These tests use FastAPI's TestClient which doesn't require a live server,
but they DO require a running PostgreSQL database (set up via docker compose).

Run with:
    docker compose exec api pytest tests/test_api.py -v
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.dependencies import get_db
from app.main import app
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.test_case import TestCase

# ── Test database setup ───────────────────────────────────────────────────────
# Uses an in-memory SQLite DB for fast, isolated tests.
# Note: Some PostgreSQL-specific features (JSONB, UUID) fall back to SQLite
# equivalents. For full fidelity, use a real Postgres test DB.

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    return eng


@pytest.fixture(scope="session", autouse=True)
def create_tables(engine):
    import asyncio

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_create())
    yield
    asyncio.get_event_loop().run_until_complete(engine.dispose())


@pytest.fixture
def client(engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_problem(client, engine):
    """Insert a sample problem with two test cases into the test DB."""
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    problem_id = uuid.uuid4()
    # Use a unique slug per test invocation to avoid UNIQUE constraint errors
    slug = f"test-hello-world-{problem_id.hex[:8]}"

    async def _insert():
        async with session_factory() as session:
            problem = Problem(
                id=problem_id,
                slug=slug,
                title="Test Hello World",
                description="## Test\n\nA test problem.",
                difficulty="easy",
                starter_code_java="public class Solution { }",
                time_limit_sec=5,
                memory_limit_mb=128,
            )
            session.add(problem)
            await session.flush()

            tc1 = TestCase(
                id=uuid.uuid4(),
                problem_id=problem.id,
                label="01",
                input_data="Alice",
                expected_output="Hello, Alice!",
                is_visible=True,
                order_index=1,
            )
            tc2 = TestCase(
                id=uuid.uuid4(),
                problem_id=problem.id,
                label="02",
                input_data="Bob",
                expected_output="Hello, Bob!",
                is_visible=False,
                order_index=2,
            )
            session.add_all([tc1, tc2])
            await session.commit()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_insert())
    finally:
        loop.close()

    yield {"id": str(problem_id), "slug": slug}



# ── Health check ──────────────────────────────────────────────────────────────

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ── GET /api/v1/problems ──────────────────────────────────────────────────────

def test_list_problems_empty(client):
    response = client.get("/api/v1/problems")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_problems_returns_problem(client, sample_problem):
    response = client.get("/api/v1/problems")
    assert response.status_code == 200
    slugs = [p["slug"] for p in response.json()]
    assert sample_problem["slug"] in slugs


# ── GET /api/v1/problems/{slug} ───────────────────────────────────────────────

def test_get_problem_not_found(client):
    response = client.get("/api/v1/problems/does-not-exist")
    assert response.status_code == 404


def test_get_problem_detail(client, sample_problem):
    slug = sample_problem["slug"]
    response = client.get(f"/api/v1/problems/{slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == slug
    assert data["title"] == "Test Hello World"
    assert data["difficulty"] == "easy"
    assert "starter_code_java" in data
    assert "test_cases" in data
    assert len(data["test_cases"]) == 2
    # Verify test case structure matches frontend contract
    tc = data["test_cases"][0]
    assert "id" in tc
    assert "label" in tc
    assert "input_data" in tc
    assert "expected_output" in tc
    assert "is_visible" in tc
    assert "order_index" in tc


# ── POST /api/v1/problems/{slug}/run ─────────────────────────────────────────

def test_run_code_returns_submission_id(client, sample_problem):
    with patch("app.worker.tasks.grade_submission.delay") as mock_delay:
        response = client.post(
            f"/api/v1/problems/{sample_problem['slug']}/run",
            json={"source_code": "public class Solution { }", "language": "java"},
        )
        assert response.status_code == 202
        data = response.json()
        assert "submission_id" in data
        assert len(data["submission_id"]) == 36  # UUID format
        mock_delay.assert_called_once_with(data["submission_id"])


def test_run_code_problem_not_found(client):
    response = client.post(
        "/api/v1/problems/nonexistent/run",
        json={"source_code": "...", "language": "java"},
    )
    assert response.status_code == 404


# ── POST /api/v1/problems/{slug}/submit ───────────────────────────────────────

def test_submit_code_returns_submission_id(client, sample_problem):
    with patch("app.worker.tasks.grade_submission.delay") as mock_delay:
        response = client.post(
            f"/api/v1/problems/{sample_problem['slug']}/submit",
            json={"source_code": "public class Solution { }", "language": "java"},
        )
        assert response.status_code == 202
        data = response.json()
        assert "submission_id" in data
        mock_delay.assert_called_once()


# ── GET /api/v1/submissions/{id} ──────────────────────────────────────────────

def test_get_submission_not_found(client):
    response = client.get(f"/api/v1/submissions/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_submission_queued(client, sample_problem):
    with patch("app.worker.tasks.grade_submission.delay"):
        run_response = client.post(
            f"/api/v1/problems/{sample_problem['slug']}/run",
            json={"source_code": "public class Solution { }", "language": "java"},
        )
        submission_id = run_response.json()["submission_id"]

    response = client.get(f"/api/v1/submissions/{submission_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == submission_id
    assert data["status"] == "queued"
    assert data["language"] == "java"
    assert data["problem_id"] == sample_problem["id"]
    assert data["score"] is None
    assert data["results_json"] is None


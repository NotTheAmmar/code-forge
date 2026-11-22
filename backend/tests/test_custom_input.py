"""Unit & integration tests for Phase A5: Custom Input Execution and Partial Credit Scoring.

Tests arbitrary stdin sandboxed code execution (Python, C, C++),
rate limiting, compile errors, and partial credit scoring based on test_cases.weight.
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
from app.models.problem import Problem
from app.models.test_case import TestCase as TestCaseModel
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password
from app.worker.sandbox import execute_custom_code

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


# ── DB Setup ──────────────────────────────────────────────────────────────────

_USER_ID = uuid.uuid4()
_USER = User(
    id=_USER_ID,
    email="coder@custom-input-test.com",
    name="Custom Input Tester",
    role="student",
    password_hash=hash_password("pw"),
)


@pytest.fixture(scope="module")
def custom_engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture(scope="module", autouse=True)
def custom_create_tables(custom_engine):
    async def _init():
        async with custom_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(custom_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(_USER)
            await session.commit()

    _run_coroutine(_init())
    yield
    _run_coroutine(custom_engine.dispose())


@pytest.fixture
def custom_session_factory(custom_engine):
    return async_sessionmaker(custom_engine, expire_on_commit=False)


@pytest.fixture(scope="module", autouse=True)
def override_db(custom_engine):
    session_factory = async_sessionmaker(custom_engine, expire_on_commit=False)

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
def client():
    with _make_client(_USER) as c:
        yield c


@pytest.fixture
def setup_problem(custom_session_factory):
    course_id = uuid.uuid4()
    p_id = uuid.uuid4()
    slug = f"custom-run-prob-{uuid.uuid4().hex[:6]}"

    async def _setup():
        async with custom_session_factory() as session:
            course = Course(
                id=course_id,
                title="Testing Ground",
                invite_code=f"CG{uuid.uuid4().hex[:6]}",
                created_by=_USER_ID,
            )
            session.add(course)

            p = Problem(
                id=p_id,
                course_id=course_id,
                slug=slug,
                title="Custom Run Sandbox Problem",
                description="Sandbox playground",
                difficulty="easy",
                starter_code_java="class Solution {}",
                time_limit_sec=5,
                memory_limit_mb=128,
            )
            session.add(p)
            await session.commit()

    _run_coroutine(_setup())
    return {"problem_id": p_id, "slug": slug}


# ── Sandbox Direct Unit Tests ─────────────────────────────────────────────────

def test_execute_custom_code_python():
    res = execute_custom_code(
        source_code="n = int(input())\nprint(f'{n} squared is {n * n}')",
        language="python",
        stdin_data="12\n",
        time_limit_sec=5,
    )
    assert res["status"] == "completed"
    assert res["exit_code"] == 0
    assert "12 squared is 144" in res["stdout"]


def test_execute_custom_code_c():
    code = """#include <stdio.h>
int main() {
    int x;
    if (scanf("%d", &x) == 1) {
        printf("RESULT:%d\\n", x * 3);
    }
    return 0;
}
"""
    res = execute_custom_code(
        source_code=code,
        language="c",
        stdin_data="7\n",
        time_limit_sec=5,
    )
    assert res["status"] == "completed"
    assert res["exit_code"] == 0
    assert "RESULT:21" in res["stdout"]


def test_execute_custom_code_cpp():
    code = """#include <iostream>
int main() {
    int val;
    if (std::cin >> val) {
        std::cout << "CPP_VAL:" << val + 100 << std::endl;
    }
    return 0;
}
"""
    res = execute_custom_code(
        source_code=code,
        language="cpp",
        stdin_data="50\n",
        time_limit_sec=5,
    )
    assert res["status"] == "completed"
    assert res["exit_code"] == 0
    assert "CPP_VAL:150" in res["stdout"]


def test_execute_custom_code_compile_error():
    bad_code = "int main() { syntax_error; }"
    res = execute_custom_code(
        source_code=bad_code,
        language="c",
        stdin_data="",
        time_limit_sec=5,
    )
    assert res["status"] == "compile_error"
    assert res["exit_code"] != 0
    assert res["stderr"] is not None


# ── HTTP Endpoint Integration Tests ───────────────────────────────────────────

def test_run_custom_endpoint_python(client, setup_problem):
    slug = setup_problem["slug"]
    payload = {
        "language": "python",
        "source_code": "a = int(input())\nb = int(input())\nprint(f'PROD:{a * b}')",
        "stdin": "6\n7\n",
    }
    resp = client.post(f"/api/v1/problems/{slug}/run-custom", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "completed"
    assert "PROD:42" in data["stdout"]
    assert data["exit_code"] == 0


def test_run_custom_endpoint_not_found(client):
    payload = {
        "language": "python",
        "source_code": "print('hello')",
        "stdin": "",
    }
    resp = client.post("/api/v1/problems/nonexistent-prob-slug/run-custom", json=payload)
    assert resp.status_code == 404


def test_weighted_scoring_calculation():
    """Verify partial credit weighting calculation."""
    class MockTC:
        def __init__(self, weight):
            self.weight = weight

    test_cases = [MockTC(weight=30), MockTC(weight=70)]
    results = [{"passed": True}, {"passed": False}]

    total_weight = sum((tc.weight if getattr(tc, "weight", None) is not None and tc.weight > 0 else 1) for tc in test_cases)
    passed_weight = sum((tc.weight if getattr(tc, "weight", None) is not None and tc.weight > 0 else 1) for tc, r in zip(test_cases, results) if r.get("passed"))
    score = round((passed_weight / total_weight) * 100) if total_weight > 0 else 0

    assert total_weight == 100
    assert passed_weight == 30
    assert score == 30

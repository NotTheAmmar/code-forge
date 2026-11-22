"""Unit & integration tests for Phase A1: Real-Time WebSocket Streaming.

Tests WebSocket connection handling, terminal status immediate replay,
invalid UUID rejection, non-existent submission handling, and Redis Pub/Sub event relay.
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.course import Course
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.websocket.submissions_ws import publish_submission_event

# ── SQLite Database Setup for isolated testing ────────────────────────────────

_TEST_USER_ID = uuid.uuid4()
_TEST_USER = User(
    id=_TEST_USER_ID,
    email="ws_tester@codeforge.io",
    name="WS Tester",
    role="instructor",
    password_hash="fakehash",
)


@pytest.fixture(scope="module")
def ws_engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture(scope="module", autouse=True)
def ws_create_tables(ws_engine):
    async def _init():
        async with ws_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(ws_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(_TEST_USER)
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_init())
    yield
    asyncio.get_event_loop().run_until_complete(ws_engine.dispose())


@pytest.fixture
def ws_session_factory(ws_engine):
    return async_sessionmaker(ws_engine, expire_on_commit=False)


@pytest.fixture
def ws_client(ws_session_factory, monkeypatch):
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with ws_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_current_user():
        return _TEST_USER

    # Point AsyncSessionLocal inside submissions_ws to our test SQLite session
    monkeypatch.setattr("app.websocket.submissions_ws.AsyncSessionLocal", ws_session_factory)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_websocket_invalid_uuid(ws_client):
    """Connecting with an invalid UUID should receive an error payload and disconnect."""
    with ws_client.websocket_connect("/api/v1/ws/submissions/invalid-uuid-format") as ws:
        msg = ws.receive_json()
        assert msg["event"] == "completed"
        assert msg["status"] == "error"
        assert "Invalid submission UUID" in msg["error"]


@pytest.mark.asyncio
async def test_websocket_nonexistent_submission(ws_client):
    """Connecting for a submission that does not exist in the database."""
    random_sub_id = str(uuid.uuid4())
    with ws_client.websocket_connect(f"/api/v1/ws/submissions/{random_sub_id}") as ws:
        msg = ws.receive_json()
        assert msg["event"] == "completed"
        assert msg["status"] == "error"
        assert f"Submission '{random_sub_id}' not found." in msg["error"]


@pytest.mark.asyncio
async def test_websocket_terminal_submission_replays_result(ws_client, ws_session_factory):
    """If submission is already completed, the terminal payload is sent immediately."""
    course_id = uuid.uuid4()
    sub_id = uuid.uuid4()
    prob_id = uuid.uuid4()

    async with ws_session_factory() as session:
        course = Course(
            id=course_id,
            title="WS Test Course",
            invite_code=f"WS{uuid.uuid4().hex[:6]}",
            created_by=_TEST_USER_ID,
        )
        session.add(course)
        await session.flush()

        prob = Problem(
            id=prob_id,
            course_id=course_id,
            slug=f"ws-prob-{uuid.uuid4().hex[:6]}",
            title="WS Problem",
            description="A test problem for WS streaming",
            difficulty="easy",
            time_limit_sec=5,
        )
        session.add(prob)
        await session.flush()

        sub = Submission(
            id=sub_id,
            problem_id=prob_id,
            user_id=_TEST_USER_ID,
            language="python",
            source_code="print('hello')",
            status="completed",
            score=100,
            passed_cases=2,
            total_cases=2,
            execution_time_ms=45,
            results_json=[
                {"test_case_id": "tc1", "passed": True, "actual_output": "hello"},
                {"test_case_id": "tc2", "passed": True, "actual_output": "hello"},
            ],
        )
        session.add(sub)
        await session.commit()

    with ws_client.websocket_connect(f"/api/v1/ws/submissions/{sub_id}") as ws:
        msg = ws.receive_json()
        assert msg["event"] == "completed"
        assert msg["submission_id"] == str(sub_id)
        assert msg["status"] == "completed"
        assert msg["score"] == 100
        assert msg["passed_cases"] == 2
        assert msg["total_cases"] == 2
        assert len(msg["results_json"]) == 2


@pytest.mark.asyncio
async def test_websocket_streaming_flow(ws_client, ws_session_factory):
    """An active submission sends initial status and forwards pubsub events until completed."""
    course_id = uuid.uuid4()
    sub_id = uuid.uuid4()
    prob_id = uuid.uuid4()

    async with ws_session_factory() as session:
        course = Course(
            id=course_id,
            title="WS Stream Course",
            invite_code=f"WSS{uuid.uuid4().hex[:6]}",
            created_by=_TEST_USER_ID,
        )
        session.add(course)
        await session.flush()

        prob = Problem(
            id=prob_id,
            course_id=course_id,
            slug=f"ws-stream-{uuid.uuid4().hex[:6]}",
            title="WS Stream Problem",
            description="Problem for live pubsub test",
            difficulty="medium",
            time_limit_sec=5,
        )
        session.add(prob)
        await session.flush()

        sub = Submission(
            id=sub_id,
            problem_id=prob_id,
            user_id=_TEST_USER_ID,
            language="java",
            source_code="class Solution {}",
            status="queued",
            score=0,
            passed_cases=0,
            total_cases=2,
        )
        session.add(sub)
        await session.commit()

    with ws_client.websocket_connect(f"/api/v1/ws/submissions/{sub_id}") as ws:
        # 1. First event should be initial status
        initial_msg = ws.receive_json()
        assert initial_msg["event"] == "status"
        assert initial_msg["status"] == "queued"
        assert initial_msg["submission_id"] == str(sub_id)

        # 2. Publish progress update
        publish_submission_event(str(sub_id), {
            "event": "test_progress",
            "submission_id": str(sub_id),
            "status": "running",
            "current_case": 1,
            "total_cases": 2,
            "case_result": {
                "test_case_id": "tc1",
                "label": "Case 1",
                "passed": True,
                "is_visible": True,
                "execution_time_ms": 12,
            },
        })

        progress_msg = ws.receive_json()
        assert progress_msg["event"] == "test_progress"
        assert progress_msg["current_case"] == 1
        assert progress_msg["case_result"]["passed"] is True

        # 3. Publish terminal completion event
        publish_submission_event(str(sub_id), {
            "event": "completed",
            "submission_id": str(sub_id),
            "problem_id": str(prob_id),
            "status": "completed",
            "score": 100,
            "passed_cases": 2,
            "total_cases": 2,
            "results_json": [
                {"test_case_id": "tc1", "passed": True},
                {"test_case_id": "tc2", "passed": True},
            ],
            "execution_time_ms": 25,
            "badge_awarded": False,
        })

        completed_msg = ws.receive_json()
        assert completed_msg["event"] == "completed"
        assert completed_msg["score"] == 100
        assert completed_msg["status"] == "completed"


@pytest.mark.asyncio
async def test_websocket_direct_mount_route(ws_client):
    """Direct route /ws/submissions/{id} functions identically to prefixed route."""
    random_sub_id = str(uuid.uuid4())
    with ws_client.websocket_connect(f"/ws/submissions/{random_sub_id}") as ws:
        msg = ws.receive_json()
        assert msg["event"] == "completed"
        assert msg["status"] == "error"

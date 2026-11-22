"""WebSocket handler for real-time submission status and test case streaming.

Protocol:
- WS /api/v1/ws/submissions/{submission_id}?token={jwt_token}
- WS /ws/submissions/{submission_id}?token={jwt_token}

Events pushed to client:
- status: {"event": "status", "submission_id": "...", "status": "queued|compiling|running", "message": "..."}
- test_progress: {"event": "test_progress", "submission_id": "...", "current_case": 1, "total_cases": 5, "case_result": {...}}
- completed: {"event": "completed", "submission_id": "...", "status": "completed|compile_error|error|timeout", "score": 100, ...}
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
import redis
import redis.asyncio as aioredis
from sqlalchemy import func, select

from app.config import settings
from app.db import AsyncSessionLocal
from app.models.badge import Badge
from app.models.submission import Submission

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

TERMINAL_STATUSES = {"completed", "compile_error", "error", "timeout"}

_redis_sync_client: redis.Redis | None = None


def get_sync_redis() -> redis.Redis:
    """Return a cached synchronous Redis client for worker thread publishing."""
    global _redis_sync_client
    if _redis_sync_client is None:
        _redis_sync_client = redis.Redis.from_url(settings.redis_url)
    return _redis_sync_client


def publish_submission_event(submission_id: str, data: dict[str, Any]) -> None:
    """Publish a submission event to the Redis Pub/Sub channel.

    Called by Celery worker and sandbox execution hooks.
    """
    try:
        r = get_sync_redis()
        channel = f"submission:{submission_id}"
        r.publish(channel, json.dumps(data))
    except Exception as exc:
        logger.warning(
            "Failed to publish submission event to channel 'submission:%s': %s",
            submission_id,
            exc,
        )


async def _build_terminal_payload(sub: Submission) -> dict[str, Any]:
    """Construct the final completed event payload from a Submission DB record."""
    badge_awarded = False
    new_badge_count = None

    if sub.lab_session_id and sub.user_id:
        try:
            async with AsyncSessionLocal() as session:
                badge_res = await session.execute(
                    select(Badge).where(
                        Badge.user_id == sub.user_id,
                        Badge.lab_session_id == sub.lab_session_id,
                        Badge.problem_id == sub.problem_id,
                    )
                )
                badge_awarded = badge_res.scalar_one_or_none() is not None

                count_res = await session.execute(
                    select(func.count(Badge.id)).where(
                        Badge.user_id == sub.user_id,
                        Badge.lab_session_id == sub.lab_session_id,
                    )
                )
                new_badge_count = count_res.scalar_one()
        except Exception:
            pass

    return {
        "event": "completed",
        "submission_id": str(sub.id),
        "problem_id": str(sub.problem_id),
        "user_id": str(sub.user_id) if sub.user_id else None,
        "language": sub.language,
        "status": sub.status,
        "score": sub.score,
        "passed_cases": sub.passed_cases,
        "total_cases": sub.total_cases,
        "results_json": sub.results_json,
        "execution_time_ms": sub.execution_time_ms,
        "badge_awarded": badge_awarded,
        "new_badge_count": new_badge_count,
    }


async def _handle_submission_ws(
    websocket: WebSocket,
    submission_id: str,
    token: str | None = None,
) -> None:
    """Core WebSocket handler for submission live streaming."""
    try:
        sub_uuid = uuid.UUID(submission_id)
    except ValueError:
        await websocket.accept()
        await websocket.send_json({
            "event": "completed",
            "status": "error",
            "error": f"Invalid submission UUID: '{submission_id}'",
        })
        await websocket.close()
        return

    # Check database state
    async with AsyncSessionLocal() as session:
        sub = await session.get(Submission, sub_uuid)
        if sub is None:
            await websocket.accept()
            await websocket.send_json({
                "event": "completed",
                "status": "error",
                "error": f"Submission '{submission_id}' not found.",
            })
            await websocket.close()
            return

        # If already terminal, push results immediately and exit
        if sub.status in TERMINAL_STATUSES:
            await websocket.accept()
            payload = await _build_terminal_payload(sub)
            await websocket.send_json(payload)
            await websocket.close()
            return

    # Accept connection for active streaming
    await websocket.accept()

    # Subscribe to Redis channel before notifying client to prevent message drops
    redis_client = aioredis.from_url(settings.redis_url)
    pubsub = redis_client.pubsub()
    channel = f"submission:{submission_id}"
    await pubsub.subscribe(channel)

    # Send initial queued/running status
    await websocket.send_json({
        "event": "status",
        "submission_id": submission_id,
        "status": sub.status,
        "message": f"Submission is currently {sub.status}...",
    })

    stop_event = asyncio.Event()

    async def redis_listener() -> None:
        """Listen to Redis channel and forward updates to WebSocket."""
        try:
            async for message in pubsub.listen():
                if stop_event.is_set():
                    break
                if not message or message.get("type") != "message":
                    continue

                raw_data = message["data"]
                data_str = (
                    raw_data.decode("utf-8")
                    if isinstance(raw_data, bytes)
                    else str(raw_data)
                )
                await websocket.send_text(data_str)

                try:
                    parsed = json.loads(data_str)
                    if (
                        parsed.get("event") == "completed"
                        or parsed.get("status") in TERMINAL_STATUSES
                    ):
                        stop_event.set()
                        break
                except Exception:
                    pass
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as exc:
            logger.warning("Error in Redis WebSocket listener for %s: %s", submission_id, exc)
        finally:
            stop_event.set()

    async def db_fallback_checker() -> None:
        """Failsafe: periodically check DB in case a race condition missed the terminal event."""
        try:
            while not stop_event.is_set():
                await asyncio.sleep(1.2)
                if stop_event.is_set():
                    break
                async with AsyncSessionLocal() as session:
                    current_sub = await session.get(Submission, sub_uuid)
                    if current_sub and current_sub.status in TERMINAL_STATUSES:
                        payload = await _build_terminal_payload(current_sub)
                        await websocket.send_json(payload)
                        stop_event.set()
                        break
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception:
            pass
        finally:
            stop_event.set()

    async def client_listener() -> None:
        """Detect client disconnects or incoming ping messages."""
        try:
            while not stop_event.is_set():
                await websocket.receive_text()
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception:
            pass
        finally:
            stop_event.set()

    listener_task = asyncio.create_task(redis_listener())
    fallback_task = asyncio.create_task(db_fallback_checker())
    client_task = asyncio.create_task(client_listener())

    try:
        # Wait until either the evaluation completes or client disconnects
        await asyncio.wait(
            [listener_task, fallback_task, client_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
    finally:
        stop_event.set()
        listener_task.cancel()
        fallback_task.cancel()
        client_task.cancel()
        await asyncio.gather(listener_task, fallback_task, client_task, return_exceptions=True)

        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await redis_client.aclose()
        except Exception:
            pass

        try:
            await websocket.close()
        except Exception:
            pass


# ── Mount points ──────────────────────────────────────────────────────────────

@router.websocket("/ws/submissions/{submission_id}")
async def submission_websocket_api(
    websocket: WebSocket,
    submission_id: str,
    token: str | None = Query(default=None),
) -> None:
    """WebSocket endpoint mounted under prefix."""
    await _handle_submission_ws(websocket, submission_id, token)


@router.websocket("/submissions/{submission_id}")
async def submission_websocket_direct(
    websocket: WebSocket,
    submission_id: str,
    token: str | None = Query(default=None),
) -> None:
    """Direct /ws/submissions/{submission_id} endpoint."""
    await _handle_submission_ws(websocket, submission_id, token)

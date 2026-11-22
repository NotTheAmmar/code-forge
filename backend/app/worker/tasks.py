"""Celery grading task definitions."""

import logging
import uuid

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="grade_submission", max_retries=0)
def grade_submission(self, submission_id: str) -> dict:
    """Grade a submission by executing it in an ephemeral Docker sandbox.

    Args:
        submission_id: UUID string of the Submission record to grade.

    Returns:
        dict with status, score, passed_cases, total_cases, results_json.
    """
    from app.worker.sandbox import execute_submission
    from app.worker.sync_db import get_sync_session
    from app.models.submission import Submission

    try:
        with get_sync_session() as session:
            sub_rec = session.get(Submission, uuid.UUID(submission_id))
            sub_lang = (sub_rec.language if sub_rec and sub_rec.language else "java").lower()
    except Exception:
        sub_lang = "unknown"

    logger.info("Starting grading task for submission %s [language=%s]", submission_id, sub_lang)

    try:
        result = execute_submission(submission_id)
        logger.info(
            "Grading complete for submission %s: status=%s score=%s",
            submission_id,
            result.get("status"),
            result.get("score"),
        )

        # Post-submission hook for badge evaluation during lab sessions
        badge_awarded = False
        new_badge_count = None
        sub_record = None

        try:
            with get_sync_session() as session:
                sub_record = session.get(Submission, uuid.UUID(submission_id))
                if sub_record and sub_record.lab_session_id and sub_record.score == 100:
                    from app.services.badge_service import evaluate_badges_sync
                    from app.models.badge import Badge
                    from sqlalchemy import func, select

                    awarded_badge = evaluate_badges_sync(session, sub_record)
                    badge_awarded = awarded_badge is not None

                    count_res = session.execute(
                        select(func.count(Badge.id)).where(
                            Badge.user_id == sub_record.user_id,
                            Badge.lab_session_id == sub_record.lab_session_id,
                        )
                    )
                    new_badge_count = count_res.scalar() or 0
        except Exception as badge_exc:
            logger.warning("Error evaluating badges for submission %s: %s", submission_id, badge_exc)

        # Publish final completed WebSocket event
        try:
            from app.websocket.submissions_ws import publish_submission_event
            publish_submission_event(submission_id, {
                "event": "completed",
                "submission_id": submission_id,
                "problem_id": str(sub_record.problem_id) if sub_record else "",
                "user_id": str(sub_record.user_id) if sub_record and sub_record.user_id else None,
                "language": sub_record.language if sub_record else sub_lang,
                "status": result.get("status"),
                "score": result.get("score"),
                "passed_cases": result.get("passed_cases"),
                "total_cases": result.get("total_cases"),
                "results_json": result.get("results_json"),
                "execution_time_ms": result.get("execution_time_ms"),
                "badge_awarded": badge_awarded,
                "new_badge_count": new_badge_count,
            })
        except Exception as pub_exc:
            logger.warning("Failed to publish completed event for %s: %s", submission_id, pub_exc)

        return result

    except Exception as exc:
        logger.exception("Unhandled error grading submission %s", submission_id)

        # Mark the submission as errored so the frontend stops polling / streaming
        try:
            with get_sync_session() as session:
                submission = session.get(Submission, uuid.UUID(submission_id))
                if submission is not None:
                    submission.status = "error"
                    submission.results_json = [{
                        "test_case_id": "system",
                        "label": "system",
                        "is_visible": True,
                        "passed": False,
                        "expected_output": None,
                        "actual_output": None,
                        "execution_time_ms": 0,
                        "error": f"Internal grading error: {exc}",
                    }]
                    session.commit()

            from app.websocket.submissions_ws import publish_submission_event
            publish_submission_event(submission_id, {
                "event": "completed",
                "submission_id": submission_id,
                "status": "error",
                "score": 0,
                "error": f"Internal grading error: {exc}",
                "results_json": [{
                    "test_case_id": "system",
                    "label": "system",
                    "is_visible": True,
                    "passed": False,
                    "expected_output": None,
                    "actual_output": None,
                    "execution_time_ms": 0,
                    "error": f"Internal grading error: {exc}",
                }],
            })
        except Exception:
            logger.exception(
                "Failed to update submission %s status to error", submission_id
            )

        raise  # Re-raise so Celery marks the task as FAILED

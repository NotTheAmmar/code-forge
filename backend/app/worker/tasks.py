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

    logger.info("Starting grading task for submission %s", submission_id)

    try:
        result = execute_submission(submission_id)
        logger.info(
            "Grading complete for submission %s: status=%s score=%s",
            submission_id,
            result.get("status"),
            result.get("score"),
        )
        return result

    except Exception as exc:
        logger.exception("Unhandled error grading submission %s", submission_id)

        # Mark the submission as errored so the frontend stops polling
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
        except Exception:
            logger.exception(
                "Failed to update submission %s status to error", submission_id
            )

        raise  # Re-raise so Celery marks the task as FAILED

"""Celery grading task definitions.

Developer A: implement the body of `grade_submission` in Phase A3.
"""

from app.worker.celery_app import celery_app


@celery_app.task(bind=True, name="grade_submission")
def grade_submission(self, submission_id: str) -> dict:
    """
    Grade a submission by executing it in an ephemeral Docker sandbox.

    Args:
        submission_id: UUID of the submission to grade.

    Returns:
        dict with status, score, passed_cases, total_cases, results_json.

    TODO (Phase A3):
        - Fetch submission + problem + test cases from DB.
        - Compile Java source in sandbox container.
        - Execute against each test case with resource limits.
        - Normalize and compare outputs.
        - Update submission record with results.
    """
    raise NotImplementedError("Implement in Phase A3 — see sandbox.py")

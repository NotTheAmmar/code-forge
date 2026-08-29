"""Pydantic schemas for Submission-related request/response shapes."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── Requests ──────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    """Payload for POST /problems/{slug}/run and /submit."""

    source_code: str
    language: str = "java"


# ── Responses ─────────────────────────────────────────────────────────────────

class SubmissionCreated(BaseModel):
    """Returned immediately after dispatching a submission to the queue."""

    submission_id: str


class TestCaseResult(BaseModel):
    """Per-test-case execution result stored in `results_json`."""

    test_case_id: str
    label: str
    is_visible: bool
    passed: bool
    expected_output: str | None
    actual_output: str | None
    execution_time_ms: int | None
    error: str | None


class SubmissionResponse(BaseModel):
    """Full submission response returned by GET /submissions/{id}.

    Field names and types must match the frontend's `Submission` TypeScript
    interface defined in `frontend/src/api/client.ts`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    problem_id: uuid.UUID
    language: str
    status: str
    score: int | None
    total_cases: int | None
    passed_cases: int | None
    results_json: list[TestCaseResult] | None
    execution_time_ms: int | None
    submitted_at: datetime

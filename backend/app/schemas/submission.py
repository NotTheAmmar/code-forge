"""Pydantic schemas for Submission-related request/response shapes and Gradebook."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Requests ──────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    """Payload for POST /problems/{id}/run (runs visible cases only)."""

    source_code: str
    language: str = "java"  # java | python


class SubmitRequest(BaseModel):
    """Payload for POST /problems/{id}/submit (full grading + lab tagging)."""

    source_code: str
    language: str = "java"  # java | python
    lab_session_id: uuid.UUID | None = None


# ── Responses ─────────────────────────────────────────────────────────────────

class SubmissionCreated(BaseModel):
    """Returned immediately after dispatching a submission to the queue."""

    submission_id: str
    status: str = "queued"


class TestCaseResult(BaseModel):
    """Per-test-case execution result stored in `results_json`."""

    test_case_id: str
    label: str
    is_visible: bool
    passed: bool
    expected_output: str | None = None
    actual_output: str | None = None
    execution_time_ms: int | None = None
    error: str | None = None


class SubmissionResponse(BaseModel):
    """Full submission response returned by GET /submissions/{id}."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    problem_id: uuid.UUID
    user_id: uuid.UUID | None = None
    lab_session_id: uuid.UUID | None = None
    language: str
    status: str
    score: int | None = None
    total_cases: int | None = None
    passed_cases: int | None = None
    results_json: list[TestCaseResult] | None = None
    execution_time_ms: int | None = None
    badge_awarded: bool = False
    new_badge_count: int | None = None
    submitted_at: datetime


class SubmissionSummaryResponse(BaseModel):
    """Summary item for student's submission history."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    language: str
    status: str
    score: int | None = None
    passed_cases: int | None = None
    total_cases: int | None = None
    is_best: bool = False
    submitted_at: datetime


# ── Gradebook ─────────────────────────────────────────────────────────────────

class GradebookProblemHeader(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    difficulty: str


class GradebookScoreItem(BaseModel):
    score: int | None = None
    passed_cases: int | None = None
    total_cases: int | None = None
    submission_id: uuid.UUID | None = None
    submitted_at: datetime | None = None


class GradebookStudentRow(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    scores: dict[str, GradebookScoreItem] = Field(default_factory=dict)


class GradebookResponse(BaseModel):
    course_id: uuid.UUID
    problems: list[GradebookProblemHeader] = Field(default_factory=list)
    students: list[GradebookStudentRow] = Field(default_factory=list)

"""Pydantic schemas for Problem-related request/response shapes."""

import uuid

from pydantic import BaseModel, ConfigDict


class TestCaseSummary(BaseModel):
    """A single test case as returned to the frontend.

    For visible test cases: all fields populated.
    For hidden test cases: `input_data` and `expected_output` are still
    included in the ProblemDetail response so the frontend knows they exist,
    but the sandbox engine will blank them in SubmissionResponse results.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    input_data: str
    expected_output: str
    is_visible: bool
    order_index: int


class ProblemSummary(BaseModel):
    """Minimal problem representation used in the problems list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    difficulty: str


class ProblemDetail(ProblemSummary):
    """Full problem detail including description, starter code, and test cases."""

    model_config = ConfigDict(from_attributes=True)

    description: str
    starter_code_java: str
    time_limit_sec: int
    memory_limit_mb: int
    test_cases: list[TestCaseSummary]

"""Pydantic schemas for Problem-related request/response shapes."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TestCaseCreate(BaseModel):
    label: str = Field(..., max_length=16)
    input_data: str
    expected_output: str
    is_visible: bool = True
    order_index: int = 0


class TestCaseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    input_data: str
    expected_output: str
    is_visible: bool
    order_index: int


class ProblemCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=128)
    title: str = Field(..., min_length=2, max_length=256)
    description: str
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    starter_code_java: str = ""
    starter_code_python: str | None = None
    time_limit_sec: int = Field(default=10, ge=1, le=60)
    memory_limit_mb: int = Field(default=128, ge=16, le=1024)
    test_cases: list[TestCaseCreate] = Field(default_factory=list)


class ProblemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    starter_code_java: str | None = None
    starter_code_python: str | None = None
    time_limit_sec: int | None = None
    memory_limit_mb: int | None = None
    test_cases: list[TestCaseCreate] | None = None


class ProblemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID | None = None
    slug: str
    title: str
    difficulty: str
    time_limit_sec: int = 10
    memory_limit_mb: int = 128
    created_at: datetime | None = None


class ProblemDetail(ProblemSummary):
    model_config = ConfigDict(from_attributes=True)

    description: str
    starter_code_java: str
    starter_code_python: str | None = None
    test_cases: list[TestCaseSummary] = Field(default_factory=list)


class BulkImportRequest(BaseModel):
    problems: list[ProblemCreate]


class BulkImportResponse(BaseModel):
    imported_count: int
    failed_count: int
    imported_slugs: list[str]
    errors: list[str] = Field(default_factory=list)

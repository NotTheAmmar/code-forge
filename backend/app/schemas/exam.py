"""Pydantic schemas for Proctored Assessment, Exams, Sessions, and Anti-Cheat Violations."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Exam Problems ─────────────────────────────────────────────────────────────

class ExamProblemItem(BaseModel):
    problem_id: uuid.UUID
    order_index: int = 0
    weight: int = 100


class ExamProblemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    difficulty: str
    weight: int
    order_index: int
    description: str = ""
    starter_code_python: str | None = None
    starter_code_java: str | None = None
    starter_code_c: str | None = None
    starter_code_cpp: str | None = None


# ── Exam CRUD Schemas ─────────────────────────────────────────────────────────

class ExamCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=256)
    description: str | None = None
    duration_minutes: int = Field(default=60, ge=5, le=360)
    starts_at: datetime
    ends_at: datetime
    is_active: bool = True
    fullscreen_required: bool = True
    tab_switch_limit: int = Field(default=3, ge=1, le=20)
    copy_paste_blocked: bool = True
    problems: list[ExamProblemItem] = Field(default_factory=list)


class ExamUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=256)
    description: str | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=360)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None
    fullscreen_required: bool | None = None
    tab_switch_limit: int | None = Field(default=None, ge=1, le=20)
    copy_paste_blocked: bool | None = None
    problems: list[ExamProblemItem] | None = None


class ExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: str | None = None
    duration_minutes: int
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    fullscreen_required: bool
    tab_switch_limit: int
    copy_paste_blocked: bool
    problem_count: int = 0
    has_session: bool = False
    session_status: str | None = None
    created_at: datetime | None = None


class ExamDetailResponse(ExamResponse):
    problems: list[ExamProblemResponse] = Field(default_factory=list)


# ── Session & Lockdown Schemas ────────────────────────────────────────────────

class ExamSessionStartResponse(BaseModel):
    session_id: uuid.UUID
    exam_id: uuid.UUID
    started_at: datetime
    duration_seconds: int
    remaining_seconds: int
    fullscreen_required: bool
    tab_switch_limit: int
    copy_paste_blocked: bool
    problems: list[ExamProblemResponse]


class ExamViolationCreate(BaseModel):
    violation_type: Literal["tab_switch", "fullscreen_exit", "copy_paste", "focus_loss"]
    details: str | None = None


class ExamViolationResponse(BaseModel):
    id: uuid.UUID
    exam_session_id: uuid.UUID
    violation_type: str
    total_violations: int
    tab_switches_remaining: int
    flagged: bool
    occurred_at: datetime


class ExamSubmitRequest(BaseModel):
    is_auto_submitted: bool = False


class ExamSessionSummary(BaseModel):
    session_id: uuid.UUID
    exam_id: uuid.UUID
    submitted_at: datetime
    is_auto_submitted: bool
    total_score: int
    problem_scores: dict[str, int]
    violation_count: int


# ── Results & Integrity Dashboard Schemas ─────────────────────────────────────

class ExamStudentResult(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    status: str  # in_progress | submitted | not_started
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    is_auto_submitted: bool = False
    total_score: int | None = None
    violation_count: int = 0
    violations: list[dict] = Field(default_factory=list)


class ExamResultsDashboard(BaseModel):
    exam_id: uuid.UUID
    title: str
    total_enrolled: int
    submissions_count: int
    average_score: float
    students: list[ExamStudentResult] = Field(default_factory=list)


class ExamMyResultResponse(BaseModel):
    exam_id: uuid.UUID
    total_score: int
    submitted_at: datetime | None = None
    is_auto_submitted: bool = False
    problem_scores: dict[str, int] = Field(default_factory=dict)

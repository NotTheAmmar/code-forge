"""Pydantic schemas for Course, Student, and Problem Analytics."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Course-Wide Analytics ─────────────────────────────────────────────────────

class SummaryStats(BaseModel):
    total_students: int
    total_submissions: int
    average_pass_rate: float
    active_students_7d: int


class ProblemPassRate(BaseModel):
    problem_id: uuid.UUID
    title: str
    difficulty: str
    submissions_count: int
    pass_rate: float
    average_score: float


class ErrorDistributionItem(BaseModel):
    error_type: str
    count: int


class SubmissionTrendItem(BaseModel):
    date: str
    count: int


class CourseAnalyticsResponse(BaseModel):
    course_id: uuid.UUID
    summary: SummaryStats
    problem_pass_rates: list[ProblemPassRate]
    common_error_distribution: list[ErrorDistributionItem]
    submission_trends: list[SubmissionTrendItem]


# ── Student Analytics ─────────────────────────────────────────────────────────

class ScoreProgressionItem(BaseModel):
    submitted_at: datetime
    problem: str
    score: int


class StudentAnalyticsResponse(BaseModel):
    user_id: uuid.UUID
    name: str
    total_submissions: int
    problems_solved: int
    badges_earned: int
    score_progression: list[ScoreProgressionItem] = Field(default_factory=list)


# ── Problem Analytics ─────────────────────────────────────────────────────────

class ProblemAnalyticsResponse(BaseModel):
    problem_id: uuid.UUID
    slug: str
    title: str
    total_submissions: int
    unique_students: int
    pass_rate: float
    language_breakdown: dict[str, int] = Field(default_factory=dict)
    average_execution_time_ms: int = 0

"""Pydantic schemas for lab sessions and badges."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LabSessionCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=256)
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    mandatory_count: int = Field(default=1, ge=1)
    problem_ids: list[uuid.UUID] = Field(default_factory=list)


class LabSessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=256)
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    mandatory_count: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    problem_ids: list[uuid.UUID] | None = None


class LabSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    mandatory_count: int
    problem_count: int = 0
    is_active: bool
    created_at: datetime


class LabProblemItem(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    difficulty: str
    order_index: int


class LabSessionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    mandatory_count: int
    is_active: bool
    problems: list[LabProblemItem] = Field(default_factory=list)
    created_at: datetime


class LabDashboardStudent(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    problems_solved: int
    mandatory_completed: bool
    badge_count: int
    last_submission_at: datetime | None = None


class LabDashboardResponse(BaseModel):
    lab_id: uuid.UUID
    title: str
    mandatory_count: int
    total_students: int
    active_students: int
    total_badges_awarded: int
    students: list[LabDashboardStudent]


class StudentLabProgressResponse(BaseModel):
    lab_id: uuid.UUID
    mandatory_count: int
    problems_solved_count: int
    mandatory_completed: bool
    badge_count: int
    solved_problem_ids: list[uuid.UUID]
    recent_badge_earned: dict[str, Any] | None = None

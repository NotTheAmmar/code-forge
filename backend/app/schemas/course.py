"""Pydantic schemas for course and enrollment management."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class CourseCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=256)
    description: str | None = None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None = None
    invite_code: str
    created_by: uuid.UUID
    role: str | None = None
    member_count: int = 0
    problem_count: int = 0
    created_at: datetime

    @computed_field
    @property
    def join_code(self) -> str:
        return self.invite_code

    @computed_field
    @property
    def instructor_id(self) -> str:
        return str(self.created_by)


class CourseDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None = None
    invite_code: str
    created_by: uuid.UUID
    user_role: str | None = None
    member_count: int = 0
    created_at: datetime

    @computed_field
    @property
    def join_code(self) -> str:
        return self.invite_code

    @computed_field
    @property
    def instructor_id(self) -> str:
        return str(self.created_by)


class CourseJoinRequest(BaseModel):
    invite_code: str | None = None
    join_code: str | None = None

    @property
    def code(self) -> str:
        return (self.invite_code or self.join_code or "").strip()


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    course_title: str | None = None
    user_id: uuid.UUID
    role: str
    joined_at: datetime


class CourseMemberResponse(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    role: str
    joined_at: datetime

"""Pydantic schemas for course and enrollment management."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class CourseJoinRequest(BaseModel):
    invite_code: str = Field(..., min_length=4, max_length=16)


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

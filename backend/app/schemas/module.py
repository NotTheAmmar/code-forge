"""Pydantic schemas for Learning Modules, Contents, and Progress tracking."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Content Schemas ───────────────────────────────────────────────────────────

class ContentCreate(BaseModel):
    content_type: Literal["text", "video", "problem"]
    title: str = Field(..., min_length=1, max_length=256)
    body: str | None = None
    problem_id: uuid.UUID | None = None
    order_index: int = 0


class ContentUpdate(BaseModel):
    content_type: Literal["text", "video", "problem"] | None = None
    title: str | None = Field(default=None, min_length=1, max_length=256)
    body: str | None = None
    problem_id: uuid.UUID | None = None
    order_index: int | None = None


class ContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: uuid.UUID
    content_type: str
    title: str
    body: str | None = None
    problem_id: uuid.UUID | None = None
    order_index: int
    created_at: datetime


# ── Module Schemas ────────────────────────────────────────────────────────────

class ModuleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    order_index: int = 0
    is_published: bool = True


class ModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    order_index: int | None = None
    is_published: bool | None = None


class ModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: str | None = None
    order_index: int
    is_published: bool
    content_count: int = 0
    is_completed: bool = False
    created_at: datetime


class ModuleDetailResponse(ModuleResponse):
    contents: list[ContentResponse] = Field(default_factory=list)


# ── Progress Schemas ──────────────────────────────────────────────────────────

class ModuleProgressUpdate(BaseModel):
    last_content_id: uuid.UUID | None = None


class ModuleProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    module_id: uuid.UUID
    user_id: uuid.UUID
    is_completed: bool
    completed_at: datetime | None = None


class CourseProgressResponse(BaseModel):
    course_id: uuid.UUID
    total_modules: int
    completed_modules: int
    progress_percentage: float
    completed_module_ids: list[uuid.UUID]

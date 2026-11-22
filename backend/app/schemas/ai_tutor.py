"""Pydantic schemas for AI Pedagogical Tutor."""

import uuid
from pydantic import BaseModel, Field


class AITutorRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Student question or request for guidance")
    source_code: str | None = Field(default=None, max_length=15000, description="Current editor code for context")
    language: str | None = Field(default="python", description="Programming language (python, java, c, cpp)")
    exam_session_id: uuid.UUID | None = Field(default=None, description="Active exam session if any")


class AITutorResponse(BaseModel):
    reply: str = Field(..., description="Pedagogical guidance and conceptual logic explanation")
    model: str = Field(..., description="Model identifier used for generation")
    is_live: bool = Field(default=True, description="Whether live Gemini API or offline pedagogical engine generated the response")

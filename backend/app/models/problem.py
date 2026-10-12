"""SQLAlchemy ORM model for the `problems` table."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Problem(Base):
    """A single coding problem scoped to a course."""

    __tablename__ = "problems"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Course this problem belongs to",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Instructor user who authored this problem",
    )
    slug: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-safe identifier for the problem",
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Problem statement in Markdown",
    )
    difficulty: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="easy | medium | hard",
    )
    starter_code_java: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="Java starter template shown in the editor",
    )
    starter_code_python: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Python starter template shown in the editor",
    )
    time_limit_sec: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        comment="Per-test-case execution timeout in seconds",
    )
    memory_limit_mb: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=128,
        comment="Container memory cap in megabytes",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    course: Mapped["Course"] = relationship(  # noqa: F821
        "Course",
        back_populates="problems",
    )
    creator: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[created_by],
    )
    test_cases: Mapped[list["TestCase"]] = relationship(  # noqa: F821
        "TestCase",
        back_populates="problem",
        cascade="all, delete-orphan",
        order_by="TestCase.order_index",
        lazy="select",
    )
    submissions: Mapped[list["Submission"]] = relationship(  # noqa: F821
        "Submission",
        back_populates="problem",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Problem slug={self.slug!r} course_id={self.course_id} difficulty={self.difficulty!r}>"

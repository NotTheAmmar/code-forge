"""SQLAlchemy ORM model for the `problems` table."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Problem(Base):
    """A single coding problem available to students."""

    __tablename__ = "problems"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    slug: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-safe identifier matching the problems/ folder name",
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Problem statement in Markdown (from description.md)",
    )
    difficulty: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="easy | medium | hard",
    )
    starter_code_java: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Java starter template shown in the editor",
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
        return f"<Problem slug={self.slug!r} difficulty={self.difficulty!r}>"

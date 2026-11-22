"""SQLAlchemy ORM model for the `exam_sessions` table."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ExamSession(Base):
    """A student's active or completed exam sitting."""

    __tablename__ = "exam_sessions"
    __table_args__ = (
        UniqueConstraint("exam_id", "user_id", name="uq_exam_session_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When the student initiated the exam and entered lockdown",
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the exam was submitted (or NULL if in progress)",
    )
    is_auto_submitted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if system submitted the exam upon timer expiry",
    )
    total_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Cumulative percentage or weighted score across all exam problems",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    exam: Mapped["Exam"] = relationship(  # noqa: F821
        "Exam",
        back_populates="sessions",
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
    )
    violations: Mapped[list["ExamViolation"]] = relationship(  # noqa: F821
        "ExamViolation",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ExamViolation.occurred_at",
    )
    submissions: Mapped[list["Submission"]] = relationship(  # noqa: F821
        "Submission",
        back_populates="exam_session",
    )

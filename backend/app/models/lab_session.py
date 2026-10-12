"""SQLAlchemy ORM models for `lab_sessions` and `lab_session_problems` tables."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class LabSession(Base):
    """A time-bounded practical lab event within a course."""

    __tablename__ = "lab_sessions"

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
    )
    title: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="e.g. 'Lab 3 — Pointers'",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    mandatory_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Number of problems required as baseline before earning badges",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    course: Mapped["Course"] = relationship(  # noqa: F821
        "Course",
        back_populates="lab_sessions",
    )
    lab_problems: Mapped[list["LabSessionProblem"]] = relationship(
        "LabSessionProblem",
        back_populates="lab_session",
        cascade="all, delete-orphan",
        order_by="LabSessionProblem.order_index",
    )
    badges: Mapped[list["Badge"]] = relationship(  # noqa: F821
        "Badge",
        back_populates="lab_session",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[list["Submission"]] = relationship(  # noqa: F821
        "Submission",
        back_populates="lab_session",
    )

    def __repr__(self) -> str:
        return f"<LabSession id={self.id} title={self.title!r} course_id={self.course_id}>"


class LabSessionProblem(Base):
    """Associates a problem with a lab session, specifying presentation order."""

    __tablename__ = "lab_session_problems"
    __table_args__ = (
        UniqueConstraint(
            "lab_session_id",
            "problem_id",
            name="uq_lab_session_problem",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lab_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lab_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    lab_session: Mapped["LabSession"] = relationship(
        "LabSession",
        back_populates="lab_problems",
    )
    problem: Mapped["Problem"] = relationship(  # noqa: F821
        "Problem",
    )

    def __repr__(self) -> str:
        return (
            f"<LabSessionProblem lab={self.lab_session_id} "
            f"problem={self.problem_id} order={self.order_index}>"
        )

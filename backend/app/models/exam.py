"""SQLAlchemy ORM models for the `exams` and `exam_problems` tables."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Exam(Base):
    """A proctored assessment event with strict anti-cheat parameters and timed duration."""

    __tablename__ = "exams"

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
        comment="Course this exam belongs to",
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        comment="Allocated exam duration in minutes",
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the exam window opens",
    )
    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the exam window closes",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Master switch to open or close access to the exam",
    )
    fullscreen_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Requires student browser to remain in full-screen mode",
    )
    tab_switch_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        comment="Allowed tab switches before student is flagged",
    )
    copy_paste_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Blocks external clipboard paste into code editor",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Instructor who configured this exam",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    course: Mapped["Course"] = relationship(  # noqa: F821
        "Course",
        back_populates="exams",
    )
    creator: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[created_by],
    )
    problems: Mapped[list["ExamProblem"]] = relationship(  # noqa: F821
        "ExamProblem",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="ExamProblem.order_index",
    )
    sessions: Mapped[list["ExamSession"]] = relationship(  # noqa: F821
        "ExamSession",
        back_populates="exam",
        cascade="all, delete-orphan",
    )


class ExamProblem(Base):
    """Association table linking problems to an exam with weight and ordering."""

    __tablename__ = "exam_problems"
    __table_args__ = (
        UniqueConstraint("exam_id", "problem_id", name="uq_exam_problem"),
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
        comment="Order of this problem in the exam interface",
    )
    weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        comment="Maximum points awarded for this problem in the exam score calculation",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    exam: Mapped["Exam"] = relationship(  # noqa: F821
        "Exam",
        back_populates="problems",
    )
    problem: Mapped["Problem"] = relationship(  # noqa: F821
        "Problem",
    )

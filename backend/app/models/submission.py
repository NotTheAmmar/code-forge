"""SQLAlchemy ORM model for the `submissions` table."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Submission(Base):
    """A single code submission — Run or Submit — with execution results."""

    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Student who submitted the code",
    )
    lab_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lab_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated lab session if submitted during an active lab",
    )
    language: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="java",
        comment="java | python",
    )
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="queued",
        comment="queued | running | completed | compile_error | error | timeout",
    )
    is_full_submit: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="False = Run (visible cases only); True = Submit (all cases)",
    )

    # ── Results (populated after grading) ─────────────────────────────────────
    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Percentage score 0-100",
    )
    total_cases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed_cases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    results_json: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Array of per-test-case result objects",
    )
    execution_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total wall-clock time across all test cases in milliseconds",
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    problem: Mapped["Problem"] = relationship(  # noqa: F821
        "Problem",
        back_populates="submissions",
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="submissions",
    )
    lab_session: Mapped["LabSession | None"] = relationship(  # noqa: F821
        "LabSession",
        back_populates="submissions",
    )

    def __repr__(self) -> str:
        return (
            f"<Submission id={self.id} user_id={self.user_id} status={self.status!r} "
            f"score={self.score} problem_id={self.problem_id}>"
        )

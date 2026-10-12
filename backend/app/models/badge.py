"""SQLAlchemy ORM model for the `badges` table."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Badge(Base):
    """A badge awarded to a student for solving an extra problem during a lab session.

    No tiers: each problem solved beyond the mandatory count awards 1 badge.
    Total badges earned for a lab = count of Badge rows for that user & lab session.
    """

    __tablename__ = "badges"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "lab_session_id",
            "problem_id",
            name="uq_user_lab_problem_badge",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
        comment="The specific problem solved that earned this badge",
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="badges",
    )
    lab_session: Mapped["LabSession"] = relationship(  # noqa: F821
        "LabSession",
        back_populates="badges",
    )
    problem: Mapped["Problem"] = relationship(  # noqa: F821
        "Problem",
    )

    def __repr__(self) -> str:
        return (
            f"<Badge user={self.user_id} lab={self.lab_session_id} "
            f"problem={self.problem_id}>"
        )

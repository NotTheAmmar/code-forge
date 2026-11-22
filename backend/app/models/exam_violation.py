"""SQLAlchemy ORM model for the `exam_violations` table."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ExamViolation(Base):
    """An anti-cheat violation event logged during an exam session."""

    __tablename__ = "exam_violations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    exam_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exam_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    violation_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="tab_switch | fullscreen_exit | copy_paste | focus_loss",
    )
    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Diagnostic context (e.g. timestamp, key combinations, or window event)",
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    session: Mapped["ExamSession"] = relationship(  # noqa: F821
        "ExamSession",
        back_populates="violations",
    )

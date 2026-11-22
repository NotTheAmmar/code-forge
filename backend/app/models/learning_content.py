"""SQLAlchemy ORM model for the `learning_contents` table."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class LearningContent(Base):
    """An individual piece of instructional material (text lesson, video, or problem link) in a module."""

    __tablename__ = "learning_contents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="text | video | problem",
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Markdown body for text lesson, or YouTube URL/embed for video lesson",
    )
    problem_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional problem link for interactive coding exercise",
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Sequential display order within the module",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    module: Mapped["LearningModule"] = relationship(  # noqa: F821
        "LearningModule",
        back_populates="contents",
    )
    problem: Mapped["Problem | None"] = relationship(  # noqa: F821
        "Problem",
    )

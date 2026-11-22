"""SQLAlchemy ORM model for the `module_progress` table."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ModuleProgress(Base):
    """Tracks a student's completion progress for a learning module."""

    __tablename__ = "module_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "module_id", name="uq_module_progress_user_module"),
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
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_contents.id", ondelete="SET NULL"),
        nullable=True,
        comment="Last viewed or completed content item in this module",
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if all content in the module has been completed",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
    )
    module: Mapped["LearningModule"] = relationship(  # noqa: F821
        "LearningModule",
        back_populates="progress_records",
    )
    content: Mapped["LearningContent | None"] = relationship(  # noqa: F821
        "LearningContent",
    )

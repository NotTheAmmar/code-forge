"""SQLAlchemy ORM model for the `learning_modules` table."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class LearningModule(Base):
    """A structured learning module within a course containing lessons, videos, and practice problems."""

    __tablename__ = "learning_modules"

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
        comment="Course this learning module belongs to",
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Sequential display order within the course",
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the module is visible to students",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Instructor who authored this module",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    course: Mapped["Course"] = relationship(  # noqa: F821
        "Course",
        back_populates="learning_modules",
    )
    creator: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[created_by],
    )
    contents: Mapped[list["LearningContent"]] = relationship(  # noqa: F821
        "LearningContent",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="LearningContent.order_index",
    )
    progress_records: Mapped[list["ModuleProgress"]] = relationship(  # noqa: F821
        "ModuleProgress",
        back_populates="module",
        cascade="all, delete-orphan",
    )

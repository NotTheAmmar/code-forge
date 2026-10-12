"""SQLAlchemy ORM model for the `courses` table."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Course(Base):
    """A classroom course containing problems, enrollments, and lab sessions."""

    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invite_code: Mapped[str] = mapped_column(
        String(16),
        unique=True,
        nullable=False,
        index=True,
        comment="6-character alphanumeric invite code",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    creator: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="created_courses",
        foreign_keys=[created_by],
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(  # noqa: F821
        "Enrollment",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    problems: Mapped[list["Problem"]] = relationship(  # noqa: F821
        "Problem",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    lab_sessions: Mapped[list["LabSession"]] = relationship(  # noqa: F821
        "LabSession",
        back_populates="course",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Course id={self.id} title={self.title!r} invite_code={self.invite_code!r}>"

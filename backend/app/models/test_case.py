"""SQLAlchemy ORM model for the `test_cases` table."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TestCase(Base):
    """A single test case (input + expected output) for a problem."""

    __tablename__ = "test_cases"

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
    label: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Short identifier matching the filename prefix, e.g. '01', '02'",
    )
    input_data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Raw stdin content fed to the program (from XX.in file)",
    )
    expected_output: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Expected stdout output for comparison (from XX.out file)",
    )
    is_visible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="True if this test case is visible to students",
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sort order derived from the label (01 → 1, 02 → 2, ...)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    problem: Mapped["Problem"] = relationship(  # noqa: F821
        "Problem",
        back_populates="test_cases",
    )

    def __repr__(self) -> str:
        return (
            f"<TestCase label={self.label!r} "
            f"visible={self.is_visible} problem_id={self.problem_id}>"
        )

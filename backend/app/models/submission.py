"""Submission ORM model — a student's graded run for an assignment."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.types import JSONBCompatible


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # JSONB — null until grading completes; stores per-criterion pass/fail + points
    checkpoint_results: Mapped[dict | None] = mapped_column(
        JSONBCompatible, nullable=True
    )
    score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    grading_status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending"
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    assignment: Mapped["Assignment"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Assignment", back_populates="submissions"
    )

"""Assignment ORM model — a graded design challenge within a course."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.types import JSONBCompatible


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    pdk: Mapped[str] = mapped_column(String, nullable=False, default="sky130hd")
    target_stage: Mapped[str] = mapped_column(String, nullable=False, default="route")

    # JSONB columns — use JSONBCompatible for JSONB on PostgreSQL, JSON on SQLite
    locked_params: Mapped[dict] = mapped_column(
        JSONBCompatible, nullable=False, default=dict
    )
    editable_params: Mapped[list] = mapped_column(
        JSONBCompatible, nullable=False, default=list
    )
    checkpoint_rules: Mapped[dict] = mapped_column(
        JSONBCompatible, nullable=False, default=dict
    )

    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    orfs_version: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="assignments")  # type: ignore[name-defined]  # noqa: F821
    submissions: Mapped[list["Submission"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Submission",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )

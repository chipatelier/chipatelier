"""Run ORM model — represents one ORFS job execution."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.types import JSONBCompatible


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    target_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    stage_completed: Mapped[str | None] = mapped_column(String, nullable=True)
    is_submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # Separate JSONB columns: ppa = metrics only, config = config.mk snapshot
    # Uses JSONBCompatible: JSONB on PostgreSQL (for GIN indexing), JSON on SQLite (tests)
    ppa: Mapped[dict | None] = mapped_column(JSONBCompatible, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONBCompatible, nullable=True)
    stage_metrics: Mapped[dict | None] = mapped_column(JSONBCompatible, nullable=True)

    celery_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="runs")  # type: ignore[name-defined]  # noqa: F821
    vnc_sessions: Mapped[list["VncSession"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "VncSession", back_populates="run"
    )

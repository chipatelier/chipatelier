"""VncSession ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class VncSession(Base):
    __tablename__ = "vnc_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id"),
        nullable=False,
    )
    container_id: Mapped[str | None] = mapped_column(String, nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="starting")
    token: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="vnc_sessions")  # type: ignore[name-defined]  # noqa: F821
    run: Mapped["Run"] = relationship("Run", back_populates="vnc_sessions")  # type: ignore[name-defined]  # noqa: F821

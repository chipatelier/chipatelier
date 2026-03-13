"""User ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="student")
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project", back_populates="user", cascade="all, delete-orphan"
    )
    vnc_sessions: Mapped[list["VncSession"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "VncSession", back_populates="user"
    )

"""Project ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    pdk: Mapped[str] = mapped_column(String, nullable=False, default="sky130hd")
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="projects")  # type: ignore[name-defined]  # noqa: F821
    runs: Mapped[list["Run"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Run", back_populates="project", cascade="all, delete-orphan"
    )

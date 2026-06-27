"""LinkedIn profile model for cached profile data."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class LinkedInProfile(BaseModel):
    """Cached LinkedIn profile data for the authenticated user."""

    __tablename__ = "linkedin_profiles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )

    member_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True, comment="LinkedIn member ID"
    )

    profile_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    last_synced_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="linkedin_profiles")

    def __repr__(self) -> str:
        return f"<LinkedInProfile(id={self.id}, member_id={self.member_id})>"

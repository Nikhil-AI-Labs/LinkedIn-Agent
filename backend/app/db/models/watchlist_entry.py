"""Watchlist entry model."""

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class WatchlistEntry(BaseModel):
    """Watchlist entry for monitoring LinkedIn profiles."""

    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "target_member_id", name="uq_user_target"),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    target_member_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="LinkedIn member ID to monitor"
    )
    target_profile_url: Mapped[str] = mapped_column(String(500), nullable=False)
    target_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", index=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="watchlist")

    def __repr__(self) -> str:
        return f"<WatchlistEntry(id={self.id}, target_member_id={self.target_member_id})>"

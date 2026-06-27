"""Browser session model for tracking browser control connections."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class BrowserSession(BaseModel):
    """Browser session tracking for Kimi WebBridge or Playwright.

    Tracks browser control connections and session state.
    """

    __tablename__ = "browser_sessions"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="kimi_webbridge",
        comment="kimi_webbridge or playwright",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="disconnected",
        comment="connected, disconnected, error",
    )

    browser_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="chrome, firefox, edge, etc."
    )

    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)

    metadata_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Provider-specific metadata (bridge version, capabilities, etc.)",
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="browser_sessions")

    def __repr__(self) -> str:
        return f"<BrowserSession(id={self.id}, provider={self.provider}, status={self.status})>"

"""User model."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class User(BaseModel):
    """User account model.

    Even for personal use, maintains user table for future multi-user support.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en", server_default="en"
    )
    voice_enabled: Mapped[bool] = mapped_column(default=False, server_default="false")

    # Relationships
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    browser_sessions: Mapped[list["BrowserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    linkedin_profiles: Mapped[list["LinkedInProfile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    posts_drafted: Mapped[list["PostDraft"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    pending_engagements: Mapped[list["PendingEngagement"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    watchlist: Mapped[list["WatchlistEntry"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    chat_history: Mapped[list["ChatMessage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    graph_runs: Mapped[list["GraphRun"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"

"""OAuth account model for LinkedIn OAuth tokens."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class OAuthAccount(BaseModel):
    """OAuth account linking for LinkedIn official API.

    Stores encrypted OAuth tokens per user. Only used when AUTH_MODE=oauth.
    """

    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="linkedin", server_default="linkedin"
    )
    provider_user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="LinkedIn member ID or sub from OpenID Connect"
    )

    # Encrypted OAuth tokens (encrypted at rest)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    token_expires_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    scope: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Granted OAuth scopes (e.g., w_member_social)"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="oauth_accounts")

    def __repr__(self) -> str:
        return f"<OAuthAccount(id={self.id}, provider={self.provider}, user_id={self.user_id})>"

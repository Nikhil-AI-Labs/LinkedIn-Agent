"""Pending engagement model."""

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class PendingEngagement(BaseModel):
    """Pending engagement action awaiting user approval."""

    __tablename__ = "pending_engagements"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    graph_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("graph_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="comment_reply, watchlist_post, etc."
    )
    source_post_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_post_urn: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    target_member_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="LinkedIn member ID of target"
    )

    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="like, celebrate, support, insightful, comment"
    )
    suggested_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Suggested comment text if action_type=comment"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="pending, approved, skipped, posted, failed",
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="pending_engagements")
    graph_run: Mapped["GraphRun"] = relationship(back_populates="pending_engagements")

    def __repr__(self) -> str:
        return f"<PendingEngagement(id={self.id}, action_type={self.action_type}, status={self.status})>"

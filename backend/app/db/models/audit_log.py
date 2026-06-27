"""Audit log model for tracking all system events."""

from uuid import UUID

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class AuditLog(BaseModel):
    """Audit log for all significant system events.

    Tracks user actions, system events, and state changes for debugging and compliance.
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="draft_created, post_published, engagement_approved, etc."
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="post_draft, pending_engagement, graph_run, etc."
    )
    entity_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)

    payload_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Event-specific data"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event_type={self.event_type})>"

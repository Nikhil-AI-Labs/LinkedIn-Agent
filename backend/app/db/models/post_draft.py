"""Post draft model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class PostDraft(BaseModel):
    """LinkedIn post draft with scoring and status tracking."""

    __tablename__ = "posts_drafted"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    graph_run_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True,
        comment="LangGraph thread_id (e.g. content_xxx_run_yyy)"
    )

    # Draft content
    idea_input: Mapped[str] = mapped_column(Text, nullable=False, comment="Original user idea")
    draft_text: Mapped[str] = mapped_column(Text, nullable=False, comment="Generated draft text")
    variant_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Draft variant number (0, 1, 2)"
    )

    # Evaluation
    score: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Score 0-100 from evaluation"
    )
    score_breakdown_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Detailed score breakdown and reasoning"
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="drafted",
        index=True,
        comment="drafted, approved, posted, failed",
    )

    final_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="User-edited final text before posting"
    )

    # LinkedIn post reference after posting
    linkedin_post_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin_post_urn: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    posted_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="posts_drafted")

    def __repr__(self) -> str:
        return f"<PostDraft(id={self.id}, status={self.status}, score={self.score})>"

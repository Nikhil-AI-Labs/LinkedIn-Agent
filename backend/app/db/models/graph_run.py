"""Graph run model for tracking LangGraph workflow executions."""

from uuid import UUID

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class GraphRun(BaseModel):
    """LangGraph workflow execution tracking.

    Tracks graph invocations, state, and results for debugging and resumption.
    """

    __tablename__ = "graph_runs"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    graph_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="content_creation, engagement_review, etc."
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="running",
        index=True,
        comment="running, waiting_human, completed, failed, cancelled",
    )

    current_node: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Current or last executed node"
    )

    input_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="Initial input")
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="Final result")
    error_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Error details if failed"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="graph_runs")

    def __repr__(self) -> str:
        return f"<GraphRun(id={self.id}, graph_name={self.graph_name}, status={self.status})>"

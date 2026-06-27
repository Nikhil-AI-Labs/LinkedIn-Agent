"""Chat message model."""

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class ChatMessage(BaseModel):
    """Chat message history."""

    __tablename__ = "chat_history"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    role: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="user, assistant, system"
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_mode: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="text, voice"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="chat_history")

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role={self.role})>"

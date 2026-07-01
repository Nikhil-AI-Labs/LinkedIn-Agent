"""Repository for chat history persistence."""

from datetime import datetime
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_message import ChatMessage
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatHistoryRepository:
    """Repository for managing chat history."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_message(
        self,
        user_id: str,
        thread_id: str,
        role: str,
        content: str,
        intent: str | None = None,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
        language: str | None = None,
        source_mode: str | None = None,
    ) -> ChatMessage:
        """Create a new chat message.
        
        Args:
            user_id: User ID
            thread_id: Thread/conversation ID (logged but not stored in model)
            role: Message role (user, assistant, system)
            content: Message content
            intent: Classified intent (optional, logged but not stored in model)
            metadata: Additional JSON metadata (optional, logged but not stored in model)
            trace_id: Trace ID for logging (optional, not stored in model)
            language: Language of the message (optional)
            source_mode: Source mode (text, voice) (optional)
            
        Returns:
            Created ChatMessage instance
        """
        message = ChatMessage(
            user_id=user_id,
            role=role,
            message_text=content,
            language=language,
            source_mode=source_mode,
        )
        
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        
        logger.info(
            "chat_message_created",
            message_id=message.id,
            user_id=user_id,
            thread_id=thread_id,
            role=role,
            intent=intent,
            trace_id=trace_id,
        )
        
        return message
    
    async def list_thread_messages(
        self,
        thread_id: str,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[ChatMessage]:
        """List messages in a thread.
        
        Note: Since thread_id is not stored in the model, this returns empty list.
        Consider using get_recent_user_context for user-based history instead.
        
        Args:
            thread_id: Thread ID (not used, for API compatibility)
            limit: Maximum number of messages to return
            before: Return messages before this timestamp (for pagination)
            
        Returns:
            Empty list (thread_id not stored in current model)
        """
        logger.warning(
            "list_thread_messages called but thread_id not in model",
            thread_id=thread_id,
        )
        
        # Return empty list since thread_id is not stored
        return []
    
    async def get_recent_user_context(
        self,
        user_id: str,
        limit: int = 20,
    ) -> list[ChatMessage]:
        """Get recent conversation context for a user across all threads.
        
        Args:
            user_id: User ID
            limit: Maximum number of messages
            
        Returns:
            List of recent ChatMessage instances
        """
        query = (
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        messages = result.scalars().all()
        
        logger.info(
            "user_context_retrieved",
            user_id=user_id,
            count=len(messages),
        )
        
        return list(messages)
    
    async def get_thread_by_id(
        self,
        thread_id: str,
    ) -> list[ChatMessage]:
        """Get all messages in a thread.
        
        Note: Since thread_id is not stored in the model, this returns empty list.
        Consider using get_recent_user_context for user-based history instead.
        
        Args:
            thread_id: Thread ID (not used, for API compatibility)
            
        Returns:
            Empty list (thread_id not stored in current model)
        """
        logger.warning(
            "get_thread_by_id called but thread_id not in model",
            thread_id=thread_id,
        )
        
        # Return empty list since thread_id is not stored
        return []

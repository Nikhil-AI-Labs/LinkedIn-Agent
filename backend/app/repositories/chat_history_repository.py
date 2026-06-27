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
        user_id: int,
        thread_id: str,
        role: str,
        content: str,
        intent: str | None = None,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> ChatMessage:
        """Create a new chat message.
        
        Args:
            user_id: User ID
            thread_id: Thread/conversation ID
            role: Message role (user, assistant, system)
            content: Message content
            intent: Classified intent (optional)
            metadata: Additional JSON metadata (optional)
            trace_id: Trace ID for logging (optional)
            
        Returns:
            Created ChatMessage instance
        """
        message = ChatMessage(
            user_id=user_id,
            thread_id=thread_id,
            role=role,
            content=content,
            intent=intent,
            metadata=metadata or {},
            trace_id=trace_id,
            created_at=datetime.utcnow(),
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
        
        Args:
            thread_id: Thread ID
            limit: Maximum number of messages to return
            before: Return messages before this timestamp (for pagination)
            
        Returns:
            List of ChatMessage instances in reverse chronological order
        """
        query = select(ChatMessage).where(ChatMessage.thread_id == thread_id)
        
        if before:
            query = query.where(ChatMessage.created_at < before)
        
        query = query.order_by(desc(ChatMessage.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        messages = result.scalars().all()
        
        logger.info(
            "thread_messages_retrieved",
            thread_id=thread_id,
            count=len(messages),
            before=before.isoformat() if before else None,
        )
        
        return list(messages)
    
    async def get_recent_user_context(
        self,
        user_id: int,
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
        
        Args:
            thread_id: Thread ID
            
        Returns:
            List of ChatMessage instances
        """
        query = (
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

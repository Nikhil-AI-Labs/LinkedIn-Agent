"""Chat service orchestration layer."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.checkpoint.postgres import PostgresSaver

from app.services.intent_router import classify_intent, IntentResult
from app.services.llm import llm_manager, LLMTask, LLMMessage
from app.repositories.chat_history_repository import ChatHistoryRepository
from app.repositories.pending_engagement_repository import PendingEngagementRepository
from app.repositories.watchlist_repository import WatchlistRepository
from app.agents.content_creation_agent import start_content_creation
from app.agents.monitoring_agent import start_monitoring
from app.agents.common import generate_thread_id
from app.core.logging import get_logger
from app.core.errors import ValidationError

logger = get_logger(__name__)


class ChatService:
    """Service for handling chat interactions."""
    
    def __init__(
        self,
        db: AsyncSession,
        checkpointer: PostgresSaver,
    ):
        self.db = db
        self.checkpointer = checkpointer
        self.chat_repo = ChatHistoryRepository(db)
    
    async def process_message(
        self,
        user_id: int,
        message: str,
        thread_id: str | None,
        trace_id: str,
    ) -> dict:
        """Process a chat message and route to appropriate handler.
        
        Args:
            user_id: User ID
            message: User message text
            thread_id: Optional existing thread ID
            trace_id: Trace ID for logging
            
        Returns:
            Response dict with intent, status, thread_id, trace_id, data
        """
        if not message or not message.strip():
            raise ValidationError("Message cannot be empty", field="message")
        
        logger.info(
            "processing_chat_message",
            user_id=user_id,
            message_length=len(message),
            has_thread=thread_id is not None,
            trace_id=trace_id,
        )
        
        # Generate thread ID if not provided
        if not thread_id:
            thread_id = generate_thread_id(user_id)
        
        # Persist user message
        await self.chat_repo.create_message(
            user_id=user_id,
            thread_id=thread_id,
            role="user",
            content=message,
            trace_id=trace_id,
        )
        
        # Classify intent
        intent_result = await classify_intent(
            text=message,
            trace_id=trace_id,
        )
        
        logger.info(
            "intent_classified",
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            trace_id=trace_id,
        )
        
        # Route by intent
        if intent_result.intent == "create_post":
            response = await self._handle_create_post(
                user_id=user_id,
                message=message,
                thread_id=thread_id,
                trace_id=trace_id,
            )
        elif intent_result.intent == "view_pending":
            response = await self._handle_view_pending(
                user_id=user_id,
                thread_id=thread_id,
                trace_id=trace_id,
            )
        elif intent_result.intent == "list_watchlist":
            response = await self._handle_list_watchlist(
                user_id=user_id,
                thread_id=thread_id,
                trace_id=trace_id,
            )
        elif intent_result.intent == "general_query":
            response = await self._handle_general_query(
                user_id=user_id,
                message=message,
                thread_id=thread_id,
                trace_id=trace_id,
            )
        else:
            # For add/remove watchlist, return instruction message
            response = {
                "intent": intent_result.intent,
                "status": "instruction",
                "thread_id": thread_id,
                "trace_id": trace_id,
                "message": self._get_intent_instruction(intent_result.intent),
                "data": intent_result.entities,
            }
        
        # Persist assistant message if present
        if response.get("message"):
            await self.chat_repo.create_message(
                user_id=user_id,
                thread_id=thread_id,
                role="assistant",
                content=response["message"],
                intent=intent_result.intent,
                trace_id=trace_id,
            )
        
        return response
    
    async def _handle_create_post(
        self,
        user_id: int,
        message: str,
        thread_id: str,
        trace_id: str,
    ) -> dict:
        """Handle post creation through content creation agent."""
        logger.info("starting_content_creation_agent", user_id=user_id, trace_id=trace_id)
        
        # Start content creation agent
        final_state = await start_content_creation(
            user_id=user_id,
            user_input=message,
            db=self.db,
            checkpointer=self.checkpointer,
        )
        
        # Extract response data
        status = final_state.get("status", "unknown")
        drafts = final_state.get("drafts", [])
        
        return {
            "intent": "create_post",
            "status": status,
            "thread_id": final_state.get("thread_id", thread_id),
            "trace_id": trace_id,
            "message": "I've created some draft options for you. Please select one or edit as needed.",
            "data": {
                "drafts": drafts,
                "scores": final_state.get("scores", {}),
            },
        }
    
    async def _handle_view_pending(
        self,
        user_id: int,
        thread_id: str,
        trace_id: str,
    ) -> dict:
        """Handle viewing pending actions."""
        pending_repo = PendingEngagementRepository(self.db)
        
        # Get pending engagements
        pending_items = await pending_repo.get_user_pending(user_id)
        
        return {
            "intent": "view_pending",
            "status": "success",
            "thread_id": thread_id,
            "trace_id": trace_id,
            "message": f"You have {len(pending_items)} pending action(s).",
            "data": {
                "pending_actions": [
                    {
                        "id": item.id,
                        "post_id": item.post_id,
                        "type": item.engagement_type.value,
                        "suggested_content": item.suggested_content,
                        "priority": item.priority,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in pending_items
                ],
                "total_count": len(pending_items),
            },
        }
    
    async def _handle_list_watchlist(
        self,
        user_id: int,
        thread_id: str,
        trace_id: str,
    ) -> dict:
        """Handle listing watchlist."""
        watchlist_repo = WatchlistRepository(self.db)
        
        # Get watchlist entries
        entries = await watchlist_repo.get_user_watchlist(user_id)
        
        return {
            "intent": "list_watchlist",
            "status": "success",
            "thread_id": thread_id,
            "trace_id": trace_id,
            "message": f"You're watching {len(entries)} profile(s).",
            "data": {
                "profiles": [
                    {
                        "id": entry.id,
                        "profile_id": entry.linkedin_profile_id,
                        "added_at": entry.added_at.isoformat(),
                    }
                    for entry in entries
                ],
                "total_count": len(entries),
            },
        }
    
    async def _handle_general_query(
        self,
        user_id: int,
        message: str,
        thread_id: str,
        trace_id: str,
    ) -> dict:
        """Handle general query with primary LLM."""
        logger.info("handling_general_query", user_id=user_id, trace_id=trace_id)
        
        # Get recent context
        recent_messages = await self.chat_repo.list_thread_messages(
            thread_id=thread_id,
            limit=10,
        )
        
        # Build conversation history
        messages = []
        for msg in reversed(recent_messages[-10:]):  # Last 10 messages in chronological order
            messages.append(
                LLMMessage(
                    role=msg.role,
                    content=msg.content,
                )
            )
        
        # Add current message if not already in history
        if not messages or messages[-1].content != message:
            messages.append(LLMMessage(role="user", content=message))
        
        # Add system message at the beginning
        messages.insert(
            0,
            LLMMessage(
                role="system",
                content="You are a helpful LinkedIn AI assistant. Provide concise, professional responses.",
            ),
        )
        
        # Call primary LLM
        response = await llm_manager.call(
            task=LLMTask.GENERAL_RESPONSE,
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            trace_id=trace_id,
        )
        
        return {
            "intent": "general_query",
            "status": "success",
            "thread_id": thread_id,
            "trace_id": trace_id,
            "message": response.content,
            "data": {},
        }
    
    def _get_intent_instruction(self, intent: str) -> str:
        """Get instruction message for intent."""
        instructions = {
            "add_watchlist": "To add a profile to your watchlist, please use the watchlist management endpoint.",
            "remove_watchlist": "To remove a profile from your watchlist, please use the watchlist management endpoint.",
            "approve_action": "To approve an action, please use the approval endpoint.",
            "skip_action": "To skip an action, please use the skip endpoint.",
        }
        return instructions.get(intent, "I can help you with that through the appropriate endpoint.")

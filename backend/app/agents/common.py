"""Common helpers for LangGraph agents."""

import uuid
from datetime import datetime
from typing import Any

import structlog
from langgraph.graph import END

from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# ID Generation
# ============================================================================

def generate_trace_id() -> str:
    """Generate a unique trace ID for request tracking."""
    return str(uuid.uuid4())


def generate_run_id() -> str:
    """Generate a unique run ID for graph execution."""
    return f"run_{uuid.uuid4().hex[:16]}"


def generate_thread_id(user_id: int) -> str:
    """Generate a unique thread ID for a user's conversation."""
    return f"user_{user_id}_{uuid.uuid4().hex[:12]}"


# ============================================================================
# Interruption Helpers
# ============================================================================

def interrupt_for_approval(
    state: dict[str, Any],
    reason: str,
    node_name: str,
) -> dict[str, Any]:
    """Mark state as requiring approval and prepare for interruption.
    
    This helper sets flags that signal the graph should interrupt.
    The actual interrupt happens when you return a node name from a conditional.
    
    Args:
        state: Current graph state
        reason: Reason for interruption (for logging/tracking)
        node_name: Name of the current node (for resume context)
        
    Returns:
        Updated state with approval flags set
    """
    logger.info(
        "graph_interrupt_requested",
        reason=reason,
        node_name=node_name,
        trace_id=state.get("trace_id"),
        run_id=state.get("run_id"),
    )
    
    state["approval_required"] = True
    state["approved"] = None  # Awaiting approval
    state["updated_at"] = datetime.utcnow()
    
    return state


def is_approved(state: dict[str, Any]) -> bool:
    """Check if the current state has been approved.
    
    Used in conditional edges after interruption.
    """
    return state.get("approved") == True


def is_rejected(state: dict[str, Any]) -> bool:
    """Check if the current state has been rejected/skipped."""
    return state.get("approved") == False


# ============================================================================
# Idempotency Guards
# ============================================================================

class IdempotencyGuard:
    """Prevent duplicate actions during graph resume/retry.
    
    Tracks completed actions in state to avoid re-executing them.
    """
    
    @staticmethod
    def mark_completed(
        state: dict[str, Any],
        action: str,
        entity_id: Any,
    ) -> dict[str, Any]:
        """Mark an action as completed for a specific entity.
        
        Args:
            state: Graph state
            action: Action identifier (e.g., "post_created", "comment_posted")
            entity_id: Entity identifier (e.g., draft_id, action_id)
        """
        if "completed_actions" not in state:
            state["completed_actions"] = {}
        
        state["completed_actions"][f"{action}:{entity_id}"] = datetime.utcnow().isoformat()
        
        logger.info(
            "action_marked_completed",
            action=action,
            entity_id=entity_id,
            trace_id=state.get("trace_id"),
        )
        
        return state
    
    @staticmethod
    def is_completed(
        state: dict[str, Any],
        action: str,
        entity_id: Any,
    ) -> bool:
        """Check if an action has already been completed.
        
        Returns:
            True if action was previously completed
        """
        completed = state.get("completed_actions", {})
        key = f"{action}:{entity_id}"
        
        is_done = key in completed
        
        if is_done:
            logger.info(
                "action_already_completed_skipping",
                action=action,
                entity_id=entity_id,
                completed_at=completed[key],
                trace_id=state.get("trace_id"),
            )
        
        return is_done


# ============================================================================
# Routing Helpers
# ============================================================================

def route_on_approval(state: dict[str, Any]) -> str:
    """Conditional edge router for approval flows.
    
    Returns:
        "approved" | "rejected" | "__end__"
    """
    if is_approved(state):
        return "approved"
    elif is_rejected(state):
        return "rejected"
    else:
        # Still waiting for approval - shouldn't reach here after interrupt
        logger.warning(
            "approval_state_unclear",
            approved=state.get("approved"),
            trace_id=state.get("trace_id"),
        )
        return "__end__"


def route_on_error(state: dict[str, Any]) -> str:
    """Conditional edge router based on error state.
    
    Returns:
        "success" | "error"
    """
    if state.get("error"):
        return "error"
    return "success"


# ============================================================================
# Error Handling
# ============================================================================

def handle_node_error(
    state: dict[str, Any],
    node_name: str,
    error: Exception,
) -> dict[str, Any]:
    """Standardized error handling for graph nodes.
    
    Args:
        state: Current graph state
        node_name: Name of the node that failed
        error: Exception that was raised
        
    Returns:
        Updated state with error information
    """
    error_msg = f"{node_name} failed: {type(error).__name__}: {str(error)}"
    
    logger.error(
        "graph_node_error",
        node_name=node_name,
        error_type=type(error).__name__,
        error=str(error),
        trace_id=state.get("trace_id"),
        run_id=state.get("run_id"),
    )
    
    state["error"] = error_msg
    state["status"] = "failed"
    state["updated_at"] = datetime.utcnow()
    
    return state


# ============================================================================
# State Validation
# ============================================================================

def validate_required_fields(
    state: dict[str, Any],
    required_fields: list[str],
    node_name: str,
) -> None:
    """Validate that required fields are present in state.
    
    Raises:
        ValueError: If any required field is missing
    """
    missing = [f for f in required_fields if f not in state or state[f] is None]
    
    if missing:
        logger.error(
            "missing_required_fields",
            node_name=node_name,
            missing_fields=missing,
            trace_id=state.get("trace_id"),
        )
        raise ValueError(
            f"{node_name}: Missing required fields: {', '.join(missing)}"
        )


# ============================================================================
# Logging Helpers
# ============================================================================

def log_node_entry(node_name: str, state: dict[str, Any]) -> None:
    """Log node entry with trace context."""
    logger.info(
        "graph_node_enter",
        node_name=node_name,
        trace_id=state.get("trace_id"),
        run_id=state.get("run_id"),
        user_id=state.get("user_id"),
    )


def log_node_exit(node_name: str, state: dict[str, Any]) -> None:
    """Log node exit with trace context."""
    logger.info(
        "graph_node_exit",
        node_name=node_name,
        trace_id=state.get("trace_id"),
        run_id=state.get("run_id"),
        status=state.get("status"),
    )

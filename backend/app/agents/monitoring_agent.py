"""Monitoring Agent - LinkedIn engagement monitoring with approval workflow.

Graph flow:
1. load_watchlist → fetch watchlist profile IDs
2. fetch_user_post_engagement → get comments/reactions on user's posts
3. fetch_watchlist_posts → get recent posts from watched profiles
4. classify_items → categorize engagement opportunities
5. generate_suggested_actions → create comment/reaction suggestions
6. persist_pending_actions → save to pending_engagements table
7. interrupt_for_approval → pause for user approval
8. post_engagement_or_skip → execute approved actions
9. mark_result → update status in DB
"""

import json
from datetime import datetime, timedelta
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.types import MonitoringState, InterruptReason
from app.agents.common import (
    generate_trace_id,
    generate_run_id,
    interrupt_for_approval,
    route_on_approval,
    IdempotencyGuard,
    handle_node_error,
    log_node_entry,
    log_node_exit,
    validate_required_fields,
)
from app.services.llm import llm_manager, LLMTask, LLMMessage
from app.repositories.watchlist_repository import WatchlistRepository
from app.repositories.pending_engagement_repository import PendingEngagementRepository
from app.core.enums import EngagementType, EngagementStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Node Functions
# ============================================================================

async def load_watchlist(
    state: MonitoringState,
    db: AsyncSession,
) -> MonitoringState:
    """Load watchlist profile IDs for the user."""
    log_node_entry("load_watchlist", state)
    
    try:
        validate_required_fields(state, ["user_id", "trace_id"], "load_watchlist")
        
        user_id = state["user_id"]
        watchlist_repo = WatchlistRepository(db)
        
        # Get active watchlist entries
        entries = await watchlist_repo.get_for_user(user_id)
        
        profile_ids = [entry.target_member_id for entry in entries]
        
        state["watchlist_profile_ids"] = profile_ids
        state["status"] = "watchlist_loaded"
        state["updated_at"] = datetime.utcnow()
        
        logger.info(
            "watchlist_loaded",
            num_profiles=len(profile_ids),
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "load_watchlist", e)
    
    log_node_exit("load_watchlist", state)
    return state


async def fetch_user_post_engagement(state: MonitoringState) -> MonitoringState:
    """Fetch comments and reactions on user's recent posts."""
    log_node_entry("fetch_user_post_engagement", state)
    
    try:
        validate_required_fields(state, ["user_id", "trace_id"], "fetch_user_post_engagement")
        
        # REAL LinkedIn integration via LinkedIn manager
        from app.services.linkedin import get_linkedin_manager
        
        linkedin_manager = get_linkedin_manager()
        
        # Fetch user's recent posts
        user_id = str(state["user_id"])
        result = await linkedin_manager.get_user_posts(
            user_id=user_id,
            limit=10,
            trace_id=state["trace_id"],
        )
        
        user_engagement = []
        if result.success and result.data:
            # Convert LinkedInPost objects to engagement items
            for post in result.data:
                user_engagement.append({
                    "id": post.post_id,
                    "type": "user_post",
                    "text": post.content,
                    "author": post.author_name or "User",
                    "author_id": post.author_id,
                    "created_at": post.created_at,
                    "comment_count": post.comment_count or 0,
                    "reaction_count": post.reaction_count or 0,
                })
        else:
            logger.warning(
                "failed_to_fetch_user_posts",
                error=result.error,
                trace_id=state["trace_id"],
            )
        
        state["user_engagement"] = user_engagement
        state["status"] = "user_engagement_fetched"
        state["updated_at"] = datetime.utcnow()
        
        logger.info(
            "user_engagement_fetched",
            num_items=len(user_engagement),
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "fetch_user_post_engagement", e)
    
    log_node_exit("fetch_user_post_engagement", state)
    return state


async def fetch_watchlist_posts(state: MonitoringState) -> MonitoringState:
    """Fetch recent posts from watchlist profiles."""
    log_node_entry("fetch_watchlist_posts", state)
    
    try:
        validate_required_fields(
            state,
            ["watchlist_profile_ids", "trace_id"],
            "fetch_watchlist_posts",
        )
        
        profile_ids = state["watchlist_profile_ids"]
        
        if not profile_ids:
            logger.info("empty_watchlist_skipping", trace_id=state["trace_id"])
            state["watchlist_posts"] = []
            return state
        
        # REAL LinkedIn integration via LinkedIn manager
        from app.services.linkedin import get_linkedin_manager
        
        linkedin_manager = get_linkedin_manager()
        
        watchlist_posts = []
        
        # Limit to 10 profiles to avoid rate limits
        for profile_id in profile_ids[:10]:
            try:
                result = await linkedin_manager.get_profile_posts(
                    member_id=profile_id,
                    limit=5,  # Last 5 posts per profile
                    trace_id=state["trace_id"],
                )
                
                if result.success and result.data:
                    # Convert LinkedInPost objects to watchlist items
                    for post in result.data:
                        watchlist_posts.append({
                            "id": post.post_id,
                            "type": "watchlist_post",
                            "text": post.content,
                            "author": post.author_name or "Unknown",
                            "author_id": post.author_id,
                            "profile_id": profile_id,
                            "created_at": post.created_at,
                            "comment_count": post.comment_count or 0,
                            "reaction_count": post.reaction_count or 0,
                        })
                else:
                    logger.warning(
                        "failed_to_fetch_profile_posts",
                        profile_id=profile_id,
                        error=result.error,
                        trace_id=state["trace_id"],
                    )
                    # Continue with other profiles
                    
            except Exception as e:
                logger.warning(
                    "exception_fetching_profile_posts",
                    profile_id=profile_id,
                    error=str(e),
                    trace_id=state["trace_id"],
                )
                # Continue with other profiles
        
        state["watchlist_posts"] = watchlist_posts
        state["status"] = "watchlist_posts_fetched"
        state["updated_at"] = datetime.utcnow()
        
        logger.info(
            "watchlist_posts_fetched",
            num_posts=len(watchlist_posts),
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "fetch_watchlist_posts", e)
    
    log_node_exit("fetch_watchlist_posts", state)
    return state


async def classify_items(state: MonitoringState) -> MonitoringState:
    """Classify engagement opportunities using fast LLM."""
    log_node_entry("classify_items", state)
    
    try:
        user_engagement = state.get("user_engagement", [])
        watchlist_posts = state.get("watchlist_posts", [])
        
        all_items = user_engagement + watchlist_posts
        
        if not all_items:
            logger.info("no_items_to_classify", trace_id=state["trace_id"])
            state["classified_items"] = []
            return state
        
        classified = []
        
        for item in all_items:
            # Use fast LLM for classification
            messages = [
                LLMMessage(
                    role="system",
                    content=(
                        "Classify this LinkedIn engagement opportunity. "
                        "Respond with JSON: {priority: 'high'|'medium'|'low', "
                        "reason: 'brief explanation', should_engage: true|false}"
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=f"Item: {json.dumps(item)}",
                ),
            ]
            
            response = await llm_manager.call(
                task=LLMTask.CLASSIFY_ENGAGEMENT,
                messages=messages,
                temperature=0.3,
                max_tokens=150,
                trace_id=state["trace_id"],
            )
            
            try:
                classification = json.loads(response.content)
            except json.JSONDecodeError:
                classification = {
                    "priority": "low",
                    "reason": "Failed to classify",
                    "should_engage": False,
                }
            
            classified_item = {
                **item,
                "classification": classification,
            }
            classified.append(classified_item)
        
        # Filter to only items we should engage with
        classified = [
            item for item in classified
            if item["classification"].get("should_engage", False)
        ]
        
        state["classified_items"] = classified
        state["status"] = "items_classified"
        state["updated_at"] = datetime.utcnow()
        
        logger.info(
            "items_classified",
            total_items=len(all_items),
            should_engage=len(classified),
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "classify_items", e)
    
    log_node_exit("classify_items", state)
    return state


async def generate_suggested_actions(state: MonitoringState) -> MonitoringState:
    """Generate comment/reaction suggestions using primary LLM."""
    log_node_entry("generate_suggested_actions", state)
    
    try:
        classified_items = state.get("classified_items", [])
        
        if not classified_items:
            logger.info("no_items_for_suggestions", trace_id=state["trace_id"])
            state["suggested_actions"] = []
            return state
        
        suggested_actions = []
        
        for item in classified_items:
            # Generate suggestion using primary LLM
            post_text = item.get("text", "")
            author = item.get("author", "Unknown")
            
            messages = [
                LLMMessage(
                    role="system",
                    content=(
                        "You are an expert at crafting thoughtful LinkedIn comments. "
                        "Write a professional, value-adding comment (2-3 sentences) "
                        "that shows genuine engagement with the post."
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=f"Post by {author}:\n{post_text}\n\nSuggest a comment:",
                ),
            ]
            
            response = await llm_manager.call(
                task=LLMTask.GENERATE_COMMENT,
                messages=messages,
                temperature=0.7,
                max_tokens=200,
                trace_id=state["trace_id"],
            )
            
            suggested_action = {
                "post_id": item.get("id"),
                "post_author": author,
                "post_text": post_text[:200],  # Truncate for storage
                "engagement_type": "comment",
                "suggested_comment": response.content,
                "priority": item["classification"].get("priority", "medium"),
                "reason": item["classification"].get("reason", ""),
            }
            
            suggested_actions.append(suggested_action)
        
        state["suggested_actions"] = suggested_actions
        state["status"] = "suggestions_generated"
        state["updated_at"] = datetime.utcnow()
        
        logger.info(
            "suggestions_generated",
            num_suggestions=len(suggested_actions),
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "generate_suggested_actions", e)
    
    log_node_exit("generate_suggested_actions", state)
    return state


async def persist_pending_actions(
    state: MonitoringState,
    db: AsyncSession,
) -> MonitoringState:
    """Save suggested actions to pending_engagements table."""
    log_node_entry("persist_pending_actions", state)
    
    try:
        validate_required_fields(
            state,
            ["user_id", "suggested_actions", "trace_id"],
            "persist_pending_actions",
        )
        
        user_id = state["user_id"]
        suggested_actions = state["suggested_actions"]
        
        if not suggested_actions:
            logger.info("no_actions_to_persist", trace_id=state["trace_id"])
            state["pending_action_ids"] = []
            return state
        
        pending_repo = PendingEngagementRepository(db)
        
        action_ids = []
        
        for action in suggested_actions:
            engagement_data = {
                "user_id": user_id,
                "post_id": action["post_id"],
                "engagement_type": EngagementType.COMMENT,
                "suggested_content": action["suggested_comment"],
                "status": EngagementStatus.PENDING,
                "priority": action.get("priority", "medium"),
                "trace_id": state["trace_id"],
            }
            
            engagement = await pending_repo.create(engagement_data)
            action_ids.append(engagement.id)
        
        state["pending_action_ids"] = action_ids
        state["status"] = "actions_persisted"
        state["updated_at"] = datetime.utcnow()
        
        logger.info(
            "actions_persisted",
            num_actions=len(action_ids),
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "persist_pending_actions", e)
    
    log_node_exit("persist_pending_actions", state)
    return state


async def interrupt_for_approval(state: MonitoringState) -> MonitoringState:
    """Interrupt for user to approve/edit suggested engagements."""
    log_node_entry("interrupt_for_approval", state)
    
    state = interrupt_for_approval(
        state,
        reason=InterruptReason.ENGAGEMENT_APPROVAL,
        node_name="interrupt_for_approval",
    )
    
    state["status"] = "awaiting_approval"
    
    log_node_exit("interrupt_for_approval", state)
    return state


async def post_engagement_or_skip(state: MonitoringState) -> MonitoringState:
    """Post approved engagement actions to LinkedIn."""
    log_node_entry("post_engagement_or_skip", state)
    
    try:
        selected_action_id = state.get("selected_action_id")
        
        if selected_action_id is None:
            logger.info("no_action_selected_skipping", trace_id=state["trace_id"])
            state["status"] = "skipped"
            return state
        
        # Check idempotency
        if IdempotencyGuard.is_completed(state, "engagement_posted", selected_action_id):
            logger.info(
                "engagement_already_posted_skipping",
                action_id=selected_action_id,
                trace_id=state["trace_id"],
            )
            return state
        
        # Get the action
        suggested_actions = state.get("suggested_actions", [])
        pending_action_ids = state.get("pending_action_ids", [])
        
        if not pending_action_ids:
            raise ValueError("No pending action IDs")
        
        # Find the action (by index for now)
        action_idx = selected_action_id
        if action_idx >= len(suggested_actions):
            raise ValueError(f"Invalid action index: {action_idx}")
        
        action = suggested_actions[action_idx]
        
        # Use user-edited content if provided
        comment_text = state.get("user_edited_comment") or action["suggested_comment"]
        
        # REAL LinkedIn integration via LinkedIn manager
        from app.services.linkedin import get_linkedin_manager
        
        linkedin_manager = get_linkedin_manager()
        
        post_id = action["post_id"]
        engagement_type = action.get("engagement_type", "comment")
        
        if engagement_type == "comment":
            # Post comment to LinkedIn
            linkedin_result = await linkedin_manager.create_comment(
                post_id=post_id,
                content=comment_text,
                trace_id=state["trace_id"],
            )
            
            if not linkedin_result.success:
                raise Exception(f"LinkedIn comment failed: {linkedin_result.error}")
            
            result = {
                "action_id": selected_action_id,
                "post_id": post_id,
                "comment_text": comment_text,
                "comment_url": linkedin_result.data.get("comment_url") if linkedin_result.data else None,
                "posted_at": datetime.utcnow().isoformat(),
            }
        else:
            # Other engagement types (reactions) can be added here
            raise ValueError(f"Unsupported engagement type: {engagement_type}")
        
        if "posted_actions" not in state:
            state["posted_actions"] = []
        
        state["posted_actions"].append(result)
        state["status"] = "engagement_posted"
        state["updated_at"] = datetime.utcnow()
        
        # Mark as completed for idempotency
        state = IdempotencyGuard.mark_completed(
            state,
            "engagement_posted",
            selected_action_id,
        )
        
        logger.info(
            "engagement_posted_successfully",
            action_id=selected_action_id,
            post_id=post_id,
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "post_engagement_or_skip", e)
    
    log_node_exit("post_engagement_or_skip", state)
    return state


async def mark_result(
    state: MonitoringState,
    db: AsyncSession,
) -> MonitoringState:
    """Update engagement status in database."""
    log_node_entry("mark_result", state)
    
    try:
        pending_action_ids = state.get("pending_action_ids", [])
        selected_action_id = state.get("selected_action_id")
        
        if not pending_action_ids:
            logger.warning("no_action_ids_to_update", trace_id=state["trace_id"])
            return state
        
        pending_repo = PendingEngagementRepository(db)
        
        for idx, action_id in enumerate(pending_action_ids):
            if idx == selected_action_id and state.get("posted_actions"):
                # Mark as completed
                await pending_repo.update_status(action_id, EngagementStatus.COMPLETED)
                logger.info("engagement_marked_completed", action_id=action_id, trace_id=state["trace_id"])
            elif state.get("approved") == False:
                # User rejected all
                await pending_repo.update_status(action_id, EngagementStatus.SKIPPED)
                logger.info("engagement_marked_skipped", action_id=action_id, trace_id=state["trace_id"])
        
    except Exception as e:
        logger.error(
            "failed_to_update_engagement_status",
            error=str(e),
            trace_id=state.get("trace_id"),
        )
        # Don't fail the whole workflow
    
    log_node_exit("mark_result", state)
    return state


# ============================================================================
# Graph Construction
# ============================================================================

def build_monitoring_graph(checkpointer: PostgresSaver) -> StateGraph:
    """Build the monitoring workflow graph.
    
    Args:
        checkpointer: PostgresSaver instance for state persistence
        
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph
    workflow = StateGraph(MonitoringState)
    
    # Add nodes
    workflow.add_node("load_watchlist", load_watchlist)
    workflow.add_node("fetch_user_post_engagement", fetch_user_post_engagement)
    workflow.add_node("fetch_watchlist_posts", fetch_watchlist_posts)
    workflow.add_node("classify_items", classify_items)
    workflow.add_node("generate_suggested_actions", generate_suggested_actions)
    workflow.add_node("persist_pending_actions", persist_pending_actions)
    workflow.add_node("interrupt_for_approval", interrupt_for_approval)
    workflow.add_node("post_engagement_or_skip", post_engagement_or_skip)
    workflow.add_node("mark_result", mark_result)
    
    # Set entry point
    workflow.set_entry_point("load_watchlist")
    
    # Add edges
    workflow.add_edge("load_watchlist", "fetch_user_post_engagement")
    workflow.add_edge("fetch_user_post_engagement", "fetch_watchlist_posts")
    workflow.add_edge("fetch_watchlist_posts", "classify_items")
    workflow.add_edge("classify_items", "generate_suggested_actions")
    workflow.add_edge("generate_suggested_actions", "persist_pending_actions")
    workflow.add_edge("persist_pending_actions", "interrupt_for_approval")
    
    # Conditional: after approval
    workflow.add_conditional_edges(
        "interrupt_for_approval",
        route_on_approval,
        {
            "approved": "post_engagement_or_skip",
            "rejected": "mark_result",  # Skip but still mark as rejected
            "__end__": "mark_result",  # Unclear state, mark and end
        },
    )
    
    workflow.add_edge("post_engagement_or_skip", "mark_result")
    workflow.add_edge("mark_result", END)
    
    # Compile with checkpointer
    graph = workflow.compile(checkpointer=checkpointer)
    
    logger.info("monitoring_graph_compiled")
    
    return graph


# ============================================================================
# Helper Functions for API Integration
# ============================================================================

async def start_monitoring(
    user_id: int,
    db: AsyncSession,
    checkpointer: PostgresSaver,
) -> dict[str, Any]:
    """Start a new monitoring workflow.
    
    Args:
        user_id: User ID
        db: Database session
        checkpointer: Graph checkpointer
        
    Returns:
        Initial state with run metadata
    """
    # Generate IDs
    trace_id = generate_trace_id()
    run_id = generate_run_id()
    thread_id = f"monitoring_{user_id}_{run_id}"
    
    # Initialize state
    initial_state: MonitoringState = {
        "user_id": user_id,
        "thread_id": thread_id,
        "trace_id": trace_id,
        "run_id": run_id,
        "intent": "monitor_engagement",
        "approval_required": False,
        "status": "started",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Build graph
    graph = build_monitoring_graph(checkpointer)
    
    # Execute until first interrupt
    config = {"configurable": {"thread_id": thread_id}}
    
    async for state in graph.astream(initial_state, config):
        logger.info("graph_state_update", state_keys=list(state.keys()), trace_id=trace_id)
    
    # Get final state
    final_state = await graph.aget_state(config)
    
    return final_state.values


async def resume_monitoring(
    thread_id: str,
    approved: bool,
    selected_action_id: int | None = None,
    user_edited_comment: str | None = None,
    checkpointer: PostgresSaver | None = None,
) -> dict[str, Any]:
    """Resume a paused monitoring workflow.
    
    Args:
        thread_id: Thread ID from initial state
        approved: Whether user approved
        selected_action_id: Index of selected action
        user_edited_comment: User's custom comment (if any)
        checkpointer: Graph checkpointer
        
    Returns:
        Updated state after resume
    """
    if not checkpointer:
        raise ValueError("Checkpointer required for resume")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Get current state
    graph = build_monitoring_graph(checkpointer)
    current_state = await graph.aget_state(config)
    
    if not current_state:
        raise ValueError(f"No state found for thread_id: {thread_id}")
    
    # Update state with user response
    updated_state = dict(current_state.values)
    updated_state["approved"] = approved
    
    if selected_action_id is not None:
        updated_state["selected_action_id"] = selected_action_id
    
    if user_edited_comment:
        updated_state["user_edited_comment"] = user_edited_comment
    
    updated_state["updated_at"] = datetime.utcnow()
    
    # Resume execution
    async for state in graph.astream(updated_state, config):
        logger.info("graph_resume_update", trace_id=updated_state.get("trace_id"))
    
    # Get final state
    final_state = await graph.aget_state(config)
    
    return final_state.values

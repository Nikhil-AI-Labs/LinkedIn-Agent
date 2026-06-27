"""Content Creation Agent - LinkedIn post generation with approval workflow.

Graph flow:
1. parse_request → extract intent and structure from user input
2. generate_drafts → create 2-3 post variants with Sarvam-105b
3. evaluate_drafts → score drafts against quality criteria
4. persist_drafts → save to posts_drafted table
5. interrupt_for_selection → pause for user to select/edit draft
6. accept_user_edit → apply user's selection or edits
7. final_approval_interrupt → pause for final approval before posting
8. post_to_linkedin → route to LinkedIn manager
9. mark_posted_or_failed → update status in DB
"""

import json
from datetime import datetime
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.types import ContentCreationState, InterruptReason
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
from app.services.llm.prompts import EVALUATE_DRAFT_PROMPT
from app.repositories.draft_repository import DraftRepository
from app.core.enums import DraftStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Node Functions
# ============================================================================

async def parse_request(state: ContentCreationState) -> ContentCreationState:
    """Parse and structure the user's content request.
    
    Extracts:
    - Topic/theme
    - Tone (professional, casual, inspirational)
    - Target audience
    - Call-to-action requirements
    - Language preference
    """
    log_node_entry("parse_request", state)
    
    try:
        validate_required_fields(state, ["user_input", "trace_id"], "parse_request")
        
        user_input = state["user_input"]
        
        # Use fast LLM to extract structured brief
        messages = [
            LLMMessage(
                role="system",
                content=(
                    "You are a content strategist. Extract key information from the user's request. "
                    "Respond with JSON containing: topic, tone, audience, cta_required, language."
                ),
            ),
            LLMMessage(
                role="user",
                content=f"Analyze this content request: {user_input}",
            ),
        ]
        
        response = await llm_manager.call(
            task=LLMTask.CLASSIFY_INTENT,
            messages=messages,
            temperature=0.3,
            max_tokens=200,
            trace_id=state["trace_id"],
        )
        
        try:
            brief = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback to simple brief
            brief = {
                "topic": user_input,
                "tone": "professional",
                "audience": "LinkedIn network",
                "cta_required": False,
                "language": "en",
            }
        
        state["brief"] = brief
        state["status"] = "brief_created"
        state["updated_at"] = datetime.utcnow()
        
        logger.info(
            "brief_created",
            brief=brief,
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "parse_request", e)
    
    log_node_exit("parse_request", state)
    return state


async def generate_drafts(state: ContentCreationState) -> ContentCreationState:
    """Generate 2-3 post draft variants using Sarvam-105b."""
    log_node_entry("generate_drafts", state)
    
    try:
        validate_required_fields(state, ["brief", "trace_id"], "generate_drafts")
        
        brief = state["brief"]
        num_variants = 3
        
        # Generate drafts using primary LLM
        messages = [
            LLMMessage(
                role="system",
                content=(
                    "You are an expert LinkedIn content creator. Write engaging, professional posts "
                    "that spark conversation and provide value. Keep posts concise (150-300 words). "
                    f"Generate {num_variants} different variants with varying hooks and styles."
                ),
            ),
            LLMMessage(
                role="user",
                content=(
                    f"Create {num_variants} LinkedIn post variants about: {brief['topic']}\n"
                    f"Tone: {brief['tone']}\n"
                    f"Audience: {brief['audience']}\n"
                    f"Include CTA: {brief['cta_required']}\n\n"
                    f"Format each variant as:\n"
                    f"VARIANT 1:\n[post text]\n\n"
                    f"VARIANT 2:\n[post text]\n\n"
                    f"VARIANT 3:\n[post text]"
                ),
            ),
        ]
        
        response = await llm_manager.call(
            task=LLMTask.DRAFT_POST,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            trace_id=state["trace_id"],
        )
        
        # Parse variants
        content = response.content
        variants = []
        
        # Simple parsing - split by "VARIANT"
        parts = content.split("VARIANT ")
        for i, part in enumerate(parts[1:], 1):  # Skip first empty part
            # Extract text after variant number
            text = part.split(":", 1)[1].strip() if ":" in part else part.strip()
            # Clean up
            text = text.split("VARIANT")[0].strip()  # Remove next variant marker
            
            if text:
                variants.append({
                    "variant_number": i,
                    "content": text,
                    "word_count": len(text.split()),
                })
        
        # If parsing failed, create single draft from full response
        if not variants:
            variants = [{
                "variant_number": 1,
                "content": content,
                "word_count": len(content.split()),
            }]
        
        state["drafts"] = variants
        state["status"] = "drafts_generated"
        state["updated_at"] = datetime.utcnow()
        
        logger.info(
            "drafts_generated",
            num_drafts=len(variants),
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "generate_drafts", e)
    
    log_node_exit("generate_drafts", state)
    return state


async def evaluate_drafts(state: ContentCreationState) -> ContentCreationState:
    """Score drafts against quality criteria."""
    log_node_entry("evaluate_drafts", state)
    
    try:
        validate_required_fields(state, ["drafts", "trace_id"], "evaluate_drafts")
        
        drafts = state["drafts"]
        scores = {}
        
        for draft in drafts:
            variant_num = draft["variant_number"]
            content = draft["content"]
            
            # Use primary LLM to evaluate
            messages = [
                LLMMessage(role="system", content=EVALUATE_DRAFT_PROMPT),
                LLMMessage(
                    role="user",
                    content=f"Evaluate this LinkedIn post:\n\n{content}",
                ),
            ]
            
            response = await llm_manager.call(
                task=LLMTask.EVALUATE_DRAFT,
                messages=messages,
                temperature=0.3,
                max_tokens=150,
                trace_id=state["trace_id"],
            )
            
            # Extract score from response (expecting format like "Score: 8.5")
            try:
                score_text = response.content
                if "score:" in score_text.lower():
                    score_part = score_text.lower().split("score:")[1].strip()
                    score = float(score_part.split()[0])
                else:
                    # Try to find first number
                    import re
                    numbers = re.findall(r"\d+\.?\d*", score_text)
                    score = float(numbers[0]) if numbers else 7.0
                
                # Clamp to 0-10
                score = max(0.0, min(10.0, score))
            except (ValueError, IndexError):
                score = 7.0  # Default score
            
            scores[f"variant_{variant_num}"] = score
            draft["score"] = score
        
        state["scores"] = scores
        state["status"] = "drafts_evaluated"
        state["updated_at"] = datetime.utcnow()
        
        logger.info(
            "drafts_evaluated",
            scores=scores,
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "evaluate_drafts", e)
    
    log_node_exit("evaluate_drafts", state)
    return state


async def persist_drafts(
    state: ContentCreationState,
    db: AsyncSession,
) -> ContentCreationState:
    """Save drafts to posts_drafted table."""
    log_node_entry("persist_drafts", state)
    
    try:
        validate_required_fields(
            state,
            ["user_id", "drafts", "trace_id"],
            "persist_drafts",
        )
        
        user_id = state["user_id"]
        drafts = state["drafts"]
        brief = state.get("brief", {})
        
        draft_repo = DraftRepository(db)
        
        # Create draft entry
        # Store all variants as JSON in a single row
        draft_data = {
            "user_id": user_id,
            "brief": json.dumps(brief),
            "variants": json.dumps(drafts),
            "status": DraftStatus.PENDING,
            "trace_id": state["trace_id"],
        }
        
        draft = await draft_repo.create(draft_data)
        
        state["draft_id"] = draft.id
        state["status"] = "drafts_persisted"
        state["updated_at"] = datetime.utcnow()
        
        logger.info(
            "drafts_persisted",
            draft_id=draft.id,
            num_variants=len(drafts),
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "persist_drafts", e)
    
    log_node_exit("persist_drafts", state)
    return state


async def interrupt_for_selection(state: ContentCreationState) -> ContentCreationState:
    """Interrupt graph for user to select or edit a draft."""
    log_node_entry("interrupt_for_selection", state)
    
    state = interrupt_for_approval(
        state,
        reason=InterruptReason.DRAFT_SELECTION,
        node_name="interrupt_for_selection",
    )
    
    state["status"] = "awaiting_selection"
    
    log_node_exit("interrupt_for_selection", state)
    return state


async def accept_user_edit(state: ContentCreationState) -> ContentCreationState:
    """Accept user's selected draft or edited content."""
    log_node_entry("accept_user_edit", state)
    
    try:
        # User can either select a variant or provide custom content
        if state.get("user_edited_content"):
            final_content = state["user_edited_content"]
            logger.info("user_provided_custom_content", trace_id=state["trace_id"])
        elif state.get("selected_draft_id") is not None:
            variant_num = state["selected_draft_id"]
            drafts = state.get("drafts", [])
            selected = next(
                (d for d in drafts if d["variant_number"] == variant_num),
                None,
            )
            if selected:
                final_content = selected["content"]
                logger.info(
                    "user_selected_variant",
                    variant_num=variant_num,
                    trace_id=state["trace_id"],
                )
            else:
                raise ValueError(f"Invalid variant selection: {variant_num}")
        else:
            # Default to highest-scored variant
            drafts = state.get("drafts", [])
            if drafts:
                best = max(drafts, key=lambda d: d.get("score", 0))
                final_content = best["content"]
                logger.info("using_highest_scored_variant", trace_id=state["trace_id"])
            else:
                raise ValueError("No drafts available")
        
        state["final_content"] = final_content
        state["status"] = "content_finalized"
        state["updated_at"] = datetime.utcnow()
        
    except Exception as e:
        state = handle_node_error(state, "accept_user_edit", e)
    
    log_node_exit("accept_user_edit", state)
    return state


async def final_approval_interrupt(state: ContentCreationState) -> ContentCreationState:
    """Final approval before posting to LinkedIn."""
    log_node_entry("final_approval_interrupt", state)
    
    state = interrupt_for_approval(
        state,
        reason=InterruptReason.FINAL_APPROVAL,
        node_name="final_approval_interrupt",
    )
    
    state["status"] = "awaiting_final_approval"
    
    log_node_exit("final_approval_interrupt", state)
    return state


async def post_to_linkedin(state: ContentCreationState) -> ContentCreationState:
    """Post content to LinkedIn via LinkedIn manager."""
    log_node_entry("post_to_linkedin", state)
    
    try:
        # Check idempotency - don't double-post
        draft_id = state.get("draft_id")
        if draft_id and IdempotencyGuard.is_completed(state, "post_created", draft_id):
            logger.info(
                "post_already_created_skipping",
                draft_id=draft_id,
                trace_id=state["trace_id"],
            )
            return state
        
        validate_required_fields(
            state,
            ["final_content", "user_id", "trace_id"],
            "post_to_linkedin",
        )
        
        final_content = state["final_content"]
        
        # REAL LinkedIn integration via LinkedIn manager
        from app.services.linkedin import get_linkedin_manager
        
        linkedin_manager = get_linkedin_manager()
        
        result = await linkedin_manager.create_post(
            content=final_content,
            trace_id=state["trace_id"],
        )
        
        post_id = result.post_id
        
        state["post_id"] = post_id
        state["status"] = "posted"
        state["updated_at"] = datetime.utcnow()
        
        # Mark as completed for idempotency
        if draft_id:
            state = IdempotencyGuard.mark_completed(state, "post_created", draft_id)
        
        logger.info(
            "post_created_successfully",
            post_id=post_id,
            trace_id=state["trace_id"],
        )
        
    except Exception as e:
        state = handle_node_error(state, "post_to_linkedin", e)
    
    log_node_exit("post_to_linkedin", state)
    return state


async def mark_posted_or_failed(
    state: ContentCreationState,
    db: AsyncSession,
) -> ContentCreationState:
    """Update draft status in database."""
    log_node_entry("mark_posted_or_failed", state)
    
    try:
        draft_id = state.get("draft_id")
        if not draft_id:
            logger.warning("no_draft_id_to_update", trace_id=state["trace_id"])
            return state
        
        draft_repo = DraftRepository(db)
        
        if state.get("error"):
            # Mark as failed
            await draft_repo.update_status(draft_id, DraftStatus.FAILED)
            logger.info("draft_marked_failed", draft_id=draft_id, trace_id=state["trace_id"])
        elif state.get("post_id"):
            # Mark as posted
            await draft_repo.update_status(draft_id, DraftStatus.POSTED)
            logger.info("draft_marked_posted", draft_id=draft_id, trace_id=state["trace_id"])
        
    except Exception as e:
        logger.error(
            "failed_to_update_draft_status",
            error=str(e),
            trace_id=state.get("trace_id"),
        )
        # Don't fail the whole workflow if status update fails
    
    log_node_exit("mark_posted_or_failed", state)
    return state


# ============================================================================
# Graph Construction
# ============================================================================

def build_content_creation_graph(checkpointer: PostgresSaver) -> StateGraph:
    """Build the content creation workflow graph.
    
    Args:
        checkpointer: PostgresSaver instance for state persistence
        
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph
    workflow = StateGraph(ContentCreationState)
    
    # Add nodes
    workflow.add_node("parse_request", parse_request)
    workflow.add_node("generate_drafts", generate_drafts)
    workflow.add_node("evaluate_drafts", evaluate_drafts)
    workflow.add_node("persist_drafts", persist_drafts)
    workflow.add_node("interrupt_for_selection", interrupt_for_selection)
    workflow.add_node("accept_user_edit", accept_user_edit)
    workflow.add_node("final_approval_interrupt", final_approval_interrupt)
    workflow.add_node("post_to_linkedin", post_to_linkedin)
    workflow.add_node("mark_posted_or_failed", mark_posted_or_failed)
    
    # Set entry point
    workflow.set_entry_point("parse_request")
    
    # Add edges
    workflow.add_edge("parse_request", "generate_drafts")
    workflow.add_edge("generate_drafts", "evaluate_drafts")
    workflow.add_edge("evaluate_drafts", "persist_drafts")
    workflow.add_edge("persist_drafts", "interrupt_for_selection")
    
    # Conditional: after draft selection
    workflow.add_conditional_edges(
        "interrupt_for_selection",
        route_on_approval,
        {
            "approved": "accept_user_edit",
            "rejected": END,  # User cancelled
        },
    )
    
    workflow.add_edge("accept_user_edit", "final_approval_interrupt")
    
    # Conditional: after final approval
    workflow.add_conditional_edges(
        "final_approval_interrupt",
        route_on_approval,
        {
            "approved": "post_to_linkedin",
            "rejected": END,  # User cancelled
        },
    )
    
    workflow.add_edge("post_to_linkedin", "mark_posted_or_failed")
    workflow.add_edge("mark_posted_or_failed", END)
    
    # Compile with checkpointer
    graph = workflow.compile(checkpointer=checkpointer)
    
    logger.info("content_creation_graph_compiled")
    
    return graph


# ============================================================================
# Helper Functions for API Integration
# ============================================================================

async def start_content_creation(
    user_id: int,
    user_input: str,
    db: AsyncSession,
    checkpointer: PostgresSaver,
) -> dict[str, Any]:
    """Start a new content creation workflow.
    
    Args:
        user_id: User ID
        user_input: User's content request
        db: Database session
        checkpointer: Graph checkpointer
        
    Returns:
        Initial state with run metadata
    """
    # Generate IDs
    trace_id = generate_trace_id()
    run_id = generate_run_id()
    thread_id = f"content_{user_id}_{run_id}"
    
    # Initialize state
    initial_state: ContentCreationState = {
        "user_id": user_id,
        "thread_id": thread_id,
        "trace_id": trace_id,
        "run_id": run_id,
        "intent": "create_post",
        "user_input": user_input,
        "messages": [],
        "approval_required": False,
        "status": "started",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Build graph
    graph = build_content_creation_graph(checkpointer)
    
    # Execute until first interrupt
    config = {"configurable": {"thread_id": thread_id}}
    
    async for state in graph.astream(initial_state, config):
        logger.info("graph_state_update", state_keys=list(state.keys()), trace_id=trace_id)
    
    # Get final state
    final_state = await graph.aget_state(config)
    
    return final_state.values


async def resume_content_creation(
    thread_id: str,
    approved: bool,
    selected_draft_id: int | None = None,
    user_edited_content: str | None = None,
    checkpointer: PostgresSaver | None = None,
) -> dict[str, Any]:
    """Resume a paused content creation workflow.
    
    Args:
        thread_id: Thread ID from initial state
        approved: Whether user approved
        selected_draft_id: Selected variant number (if any)
        user_edited_content: User's custom content (if any)
        checkpointer: Graph checkpointer
        
    Returns:
        Updated state after resume
    """
    if not checkpointer:
        raise ValueError("Checkpointer required for resume")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Get current state
    graph = build_content_creation_graph(checkpointer)
    current_state = await graph.aget_state(config)
    
    if not current_state:
        raise ValueError(f"No state found for thread_id: {thread_id}")
    
    # Update state with user response
    updated_state = dict(current_state.values)
    updated_state["approved"] = approved
    
    if selected_draft_id is not None:
        updated_state["selected_draft_id"] = selected_draft_id
    
    if user_edited_content:
        updated_state["user_edited_content"] = user_edited_content
    
    updated_state["updated_at"] = datetime.utcnow()
    
    # Resume execution
    async for state in graph.astream(updated_state, config):
        logger.info("graph_resume_update", trace_id=updated_state.get("trace_id"))
    
    # Get final state
    final_state = await graph.aget_state(config)
    
    return final_state.values

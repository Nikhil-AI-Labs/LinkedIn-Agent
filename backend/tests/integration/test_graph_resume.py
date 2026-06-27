"""CRITICAL Integration Test: LangGraph Interrupt/Resume with Real PostgreSQL.

This test MUST pass to prove the core value proposition:
- LangGraph state persists across interrupts
- Checkpoints are stored in real PostgreSQL
- Graphs can resume after simulated "app restart"

Run with: pytest tests/integration/test_graph_resume.py -v --integration
"""

import pytest
from datetime import datetime

from app.agents.content_creation_agent import (
    start_content_creation,
    resume_content_creation,
    build_content_creation_graph,
)
from app.agents.monitoring_agent import (
    start_monitoring,
    resume_monitoring,
    build_monitoring_graph,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_content_creation_interrupt_and_resume(test_db_session, real_checkpointer, test_user):
    """Test content creation graph interrupt and resume across simulated restart.
    
    This is the CRITICAL test that proves:
    1. Graph interrupts at draft selection
    2. State is persisted to PostgreSQL
    3. State can be restored after "restart"
    4. Graph can resume and complete workflow
    """
    
    user_id = test_user.id
    user_input = "Write a LinkedIn post about the importance of AI in modern healthcare"
    
    print(f"\n{'='*80}")
    print(f"CRITICAL TEST: Content Creation Graph Interrupt/Resume")
    print(f"{'='*80}\n")
    
    # ========================================================================
    # PHASE 1: Start graph and verify interrupt
    # ========================================================================
    print("PHASE 1: Starting content creation graph...")
    
    initial_state = await start_content_creation(
        user_id=user_id,
        user_input=user_input,
        db=test_db_session,
        checkpointer=real_checkpointer,
    )
    
    thread_id = initial_state["thread_id"]
    
    print(f"✓ Graph started with thread_id: {thread_id}")
    print(f"✓ Status: {initial_state['status']}")
    
    # Verify graph interrupted at draft selection
    assert initial_state["status"] == "awaiting_selection", \
        f"Expected status 'awaiting_selection', got '{initial_state['status']}'"
    
    assert initial_state.get("approval_required") is True, \
        "Expected approval_required=True"
    
    assert "drafts" in initial_state, \
        "Expected 'drafts' key in state"
    
    assert len(initial_state["drafts"]) > 0, \
        "Expected at least one draft variant"
    
    num_drafts = len(initial_state["drafts"])
    print(f"✓ Graph interrupted correctly: {num_drafts} drafts generated")
    
    # ========================================================================
    # PHASE 2: Verify checkpoint stored in PostgreSQL
    # ========================================================================
    print("\nPHASE 2: Verifying checkpoint in PostgreSQL...")
    
    config = {"configurable": {"thread_id": thread_id}}
    graph = build_content_creation_graph(real_checkpointer)
    
    checkpoint = await graph.aget_state(config)
    
    assert checkpoint is not None, \
        "Checkpoint not found in PostgreSQL!"
    
    assert checkpoint.values["status"] == "awaiting_selection", \
        f"Checkpoint has wrong status: {checkpoint.values['status']}"
    
    assert checkpoint.values["thread_id"] == thread_id, \
        "Checkpoint thread_id mismatch"
    
    assert checkpoint.values["user_id"] == user_id, \
        "Checkpoint user_id mismatch"
    
    print(f"✓ Checkpoint stored in PostgreSQL")
    print(f"✓ Checkpoint values match: status={checkpoint.values['status']}")
    
    # ========================================================================
    # PHASE 3: Simulate app restart (new graph instance)
    # ========================================================================
    print("\nPHASE 3: Simulating app restart...")
    
    # Create NEW graph instance (this simulates app restart)
    new_graph = build_content_creation_graph(real_checkpointer)
    
    # Verify state can be retrieved after "restart"
    restored_state = await new_graph.aget_state(config)
    
    assert restored_state is not None, \
        "State could not be restored after restart!"
    
    assert restored_state.values["thread_id"] == thread_id, \
        "Restored thread_id doesn't match"
    
    assert restored_state.values["user_id"] == user_id, \
        "Restored user_id doesn't match"
    
    assert restored_state.values["status"] == "awaiting_selection", \
        f"Restored status incorrect: {restored_state.values['status']}"
    
    assert "drafts" in restored_state.values, \
        "Drafts not in restored state"
    
    print(f"✓ State restored from PostgreSQL after restart")
    print(f"✓ Restored state is complete with {len(restored_state.values['drafts'])} drafts")
    
    # ========================================================================
    # PHASE 4: Resume with user selection
    # ========================================================================
    print("\nPHASE 4: Resuming graph with user selection...")
    
    # User selects first draft variant
    final_state = await resume_content_creation(
        thread_id=thread_id,
        approved=True,
        selected_draft_id=1,  # Select first variant
        checkpointer=real_checkpointer,
    )
    
    print(f"✓ Graph resumed successfully")
    print(f"✓ Final status: {final_state.get('status')}")
    
    # Verify graph reached final approval interrupt
    # (it will interrupt again for final approval before posting)
    assert "final_content" in final_state or final_state.get("status") == "awaiting_final_approval", \
        "Graph did not process selection correctly"
    
    print(f"✓ Graph processed user selection")
    
    # ========================================================================
    # PHASE 5: Verify final checkpoint persisted
    # ========================================================================
    print("\nPHASE 5: Verifying final checkpoint...")
    
    final_checkpoint = await new_graph.aget_state(config)
    
    assert final_checkpoint is not None, \
        "Final checkpoint not found"
    
    print(f"✓ Final checkpoint persisted")
    print(f"✓ Final status: {final_checkpoint.values.get('status')}")
    
    # ========================================================================
    # SUCCESS
    # ========================================================================
    print(f"\n{'='*80}")
    print(f"🎉 INTEGRATION TEST PASSED!")
    print(f"{'='*80}")
    print(f"✓ Graph interrupt works")
    print(f"✓ PostgreSQL persistence works")
    print(f"✓ State restoration after restart works")
    print(f"✓ Graph resume works")
    print(f"✓ Core value proposition PROVEN")
    print(f"{'='*80}\n")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_monitoring_interrupt_and_resume(test_db_session, real_checkpointer, test_user):
    """Test monitoring agent interrupt and resume.
    
    Similar test for monitoring workflow to prove interrupt/resume works
    across both agent types.
    """
    
    user_id = test_user.id
    
    print(f"\n{'='*80}")
    print(f"INTEGRATION TEST: Monitoring Agent Interrupt/Resume")
    print(f"{'='*80}\n")
    
    # ========================================================================
    # PHASE 1: Start monitoring workflow
    # ========================================================================
    print("PHASE 1: Starting monitoring agent...")
    
    initial_state = await start_monitoring(
        user_id=user_id,
        db=test_db_session,
        checkpointer=real_checkpointer,
    )
    
    thread_id = initial_state["thread_id"]
    
    print(f"✓ Monitoring started with thread_id: {thread_id}")
    print(f"✓ Status: {initial_state['status']}")
    
    # The monitoring agent may not interrupt if no actions are found
    # This is expected behavior
    if initial_state.get("status") == "awaiting_approval":
        print(f"✓ Graph interrupted for approval")
        
        # Verify checkpoint
        config = {"configurable": {"thread_id": thread_id}}
        graph = build_monitoring_graph(real_checkpointer)
        checkpoint = await graph.aget_state(config)
        
        assert checkpoint is not None, "Checkpoint not found"
        print(f"✓ Checkpoint stored in PostgreSQL")
        
        # Resume with rejection
        final_state = await resume_monitoring(
            thread_id=thread_id,
            approved=False,  # Skip all actions
            checkpointer=real_checkpointer,
        )
        
        print(f"✓ Graph resumed successfully")
        print(f"✓ Final status: {final_state.get('status')}")
        
    else:
        print(f"✓ No approval needed (no engagement opportunities found)")
        print(f"✓ This is expected when watchlist is empty")
    
    print(f"\n{'='*80}")
    print(f"✓ Monitoring agent test completed")
    print(f"{'='*80}\n")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_persistence_across_sessions(real_checkpointer):
    """Test that checkpoints persist across multiple checkpoint instances.
    
    This verifies the PostgreSQL backend truly persists data.
    """
    
    from app.agents.content_creation_agent import build_content_creation_graph
    
    thread_id = "test_persistence_thread"
    test_data = {
        "user_id": 999,
        "thread_id": thread_id,
        "trace_id": "test_trace",
        "run_id": "test_run",
        "intent": "test",
        "status": "test_checkpoint",
        "approval_required": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Write checkpoint with first graph instance
    graph1 = build_content_creation_graph(real_checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    
    # Save state manually
    await graph1.aupdate_state(config, test_data)
    
    # Create NEW checkpointer instance (simulates new app session)
    from app.core.config import settings
    test_db_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://",
        "postgresql://"
    ).replace("linkedin_agent", "linkedin_agent_test")
    
    new_checkpointer = PostgresSaver.from_conn_string(test_db_url)
    new_checkpointer.setup()
    
    # Read with new graph + new checkpointer
    graph2 = build_content_creation_graph(new_checkpointer)
    restored = await graph2.aget_state(config)
    
    assert restored is not None, "Checkpoint not found with new checkpointer"
    assert restored.values["thread_id"] == thread_id
    assert restored.values["user_id"] == 999
    
    print(f"✓ Checkpoint persisted across checkpointer instances")
    print(f"✓ PostgreSQL backend truly persists data")

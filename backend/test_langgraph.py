import asyncio
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

class State(TypedDict, total=False):
    count: int
    approved: bool | None
    final_content: str | None
    drafts: list[dict]
    selected_draft_id: int | None

def node1(state: State):
    state["count"] = 1
    state["approved"] = None
    state["drafts"] = [{"variant_number": 1, "content": "draft 1"}]
    return state

from langgraph.errors import NodeInterrupt

def node2(state: State):
    drafts = state.get("drafts", [])
    vid = state.get("selected_draft_id")
    selected = next((d for d in drafts if d["variant_number"] == vid), None)
    if selected:
        state["final_content"] = selected["content"]
    else:
        state["final_content"] = "NONE_FOUND"
    state["approved"] = None
    return state

def node3(state: State):
    if state.get("approved") is None:
        raise NodeInterrupt("Interrupt!")
    return state

def route(state: State):
    if state.get("approved"):
        return "node2"
    return END

def route2(state: State):
    if state.get("approved"):
        return "node4"
    return END

def node4(state: State):
    print("Executing node4! final_content is:", state.get("final_content"))
    return state

def build():
    workflow = StateGraph(State)
    workflow.add_node("node1", node1)
    workflow.add_node("node2", node2)
    workflow.add_node("node3", node3)
    workflow.add_node("node4", node4)
    workflow.set_entry_point("node1")
    workflow.add_conditional_edges("node1", route, {"node2": "node2", END: END})
    workflow.add_edge("node2", "node3")
    workflow.add_conditional_edges("node3", route2, {"node4": "node4", END: END})
    workflow.add_edge("node4", END)
    return workflow.compile(checkpointer=MemorySaver())

async def main():
    graph = build()
    config = {"configurable": {"thread_id": "1"}}
    
    # Run until first interrupt (which goes to END because approved=None)
    print("Initial run...")
    async for s in graph.astream({"count": 0}, config):
        pass
        
    state = await graph.aget_state(config)
    print("State after initial run:", state.values)
    print("Next after initial run:", state.next)
    
    # Resume from node1
    print("\nResuming from node1...")
    await graph.aupdate_state(config, {"approved": True, "selected_draft_id": 1}, as_node="node1")
    
    # Check next after update
    state = await graph.aget_state(config)
    print("State after update:", state.values)
    print("Next after update:", state.next)
    
    # Continue
    async for s in graph.astream(None, config):
        print("Stepped:", s)
        
    state = await graph.aget_state(config)
    print("Final state:", state.values)

    # Resume from node3
    print("\nResuming from node3...")
    await graph.aupdate_state(config, {"approved": True}, as_node="node3")
    
    # Check next after update
    state = await graph.aget_state(config)
    print("State after update2:", state.values)
    print("Next after update2:", state.next)
    
    # Continue
    async for s in graph.astream(None, config):
        print("Stepped 2:", s)
        
    state = await graph.aget_state(config)
    print("Final state 2:", state.values)

if __name__ == "__main__":
    asyncio.run(main())

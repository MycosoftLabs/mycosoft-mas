"""
LangGraph Proof-of-Concept for MAS v2 Orchestration
Run: python scripts/langgraph_poc.py

This demonstrates LangGraph's multi-agent coordination capabilities
as an enhancement for the MAS v2 orchestrator.
"""

from typing import TypedDict, Annotated, Sequence
import operator
import json
from datetime import datetime

# Check LangGraph availability
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


# ================== State Definition ==================

class MASState(TypedDict):
    """Shared state for multi-agent system"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_task: dict | None
    agent_outputs: dict
    next_agent: str
    iteration_count: int


# ================== Agent Functions ==================

def ceo_agent(state: MASState) -> MASState:
    """CEO: Analyzes task and delegates to appropriate agent"""
    task = state.get("current_task", {})
    task_type = task.get("type", "").lower() if task else ""
    
    # Routing logic
    if "research" in task_type or "data" in task_type:
        next_agent = "researcher"
    elif "security" in task_type:
        next_agent = "security"
    elif "database" in task_type or "mindex" in task_type:
        next_agent = "mindex"
    else:
        next_agent = "cto"
    
    output = {
        "agent": "CEO",
        "action": "delegate",
        "delegated_to": next_agent,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=json.dumps(output))],
        "agent_outputs": {**state.get("agent_outputs", {}), "ceo": output},
        "next_agent": next_agent,
        "iteration_count": state.get("iteration_count", 0) + 1
    }


def cto_agent(state: MASState) -> MASState:
    """CTO: Technical analysis and architecture decisions"""
    output = {
        "agent": "CTO",
        "action": "technical_review",
        "status": "approved",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=json.dumps(output))],
        "agent_outputs": {**state.get("agent_outputs", {}), "cto": output},
        "next_agent": "end"
    }


def researcher_agent(state: MASState) -> MASState:
    """Researcher: Data analysis and research tasks"""
    output = {
        "agent": "Researcher",
        "action": "analyze",
        "findings": ["Data collected", "Analysis complete"],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=json.dumps(output))],
        "agent_outputs": {**state.get("agent_outputs", {}), "researcher": output},
        "next_agent": "mindex",
        "iteration_count": state.get("iteration_count", 0) + 1
    }


def mindex_agent(state: MASState) -> MASState:
    """MINDEX: Database operations"""
    output = {
        "agent": "MINDEX",
        "action": "store",
        "status": "synced",
        "hash": "0x" + "a" * 16,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=json.dumps(output))],
        "agent_outputs": {**state.get("agent_outputs", {}), "mindex": output},
        "next_agent": "end"
    }


def security_agent(state: MASState) -> MASState:
    """Security: Threat analysis"""
    output = {
        "agent": "Security",
        "action": "scan",
        "threat_level": "low",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=json.dumps(output))],
        "agent_outputs": {**state.get("agent_outputs", {}), "security": output},
        "next_agent": "end"
    }


# ================== Router ==================

def route_agent(state: MASState) -> str:
    """Route to next agent based on state"""
    next_agent = state.get("next_agent", "end")
    if state.get("iteration_count", 0) > 10:
        return "end"
    return next_agent if next_agent in ["cto", "researcher", "mindex", "security"] else "end"


# ================== Build Graph ==================

def build_workflow():
    """Build the LangGraph workflow"""
    workflow = StateGraph(MASState)
    
    # Add nodes
    workflow.add_node("ceo", ceo_agent)
    workflow.add_node("cto", cto_agent)
    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("mindex", mindex_agent)
    workflow.add_node("security", security_agent)
    
    # Set entry
    workflow.set_entry_point("ceo")
    
    # Add conditional edges from CEO
    workflow.add_conditional_edges(
        "ceo",
        route_agent,
        {"cto": "cto", "researcher": "researcher", "mindex": "mindex", "security": "security", "end": END}
    )
    
    # Add edges from other agents
    workflow.add_conditional_edges("researcher", route_agent, {"mindex": "mindex", "end": END})
    workflow.add_edge("cto", END)
    workflow.add_edge("mindex", END)
    workflow.add_edge("security", END)
    
    # Compile with checkpointing
    return workflow.compile(checkpointer=MemorySaver())


# ================== Run ==================

def run_task(task: dict, session_id: str = "test"):
    """Execute a task through the workflow"""
    app = build_workflow()
    
    initial_state: MASState = {
        "messages": [HumanMessage(content=f"Task: {json.dumps(task)}")],
        "current_task": task,
        "agent_outputs": {},
        "next_agent": "ceo",
        "iteration_count": 0
    }
    
    result = app.invoke(initial_state, {"configurable": {"thread_id": session_id}})
    
    return {
        "success": True,
        "agents_executed": list(result.get("agent_outputs", {}).keys()),
        "outputs": result.get("agent_outputs", {}),
        "iterations": result.get("iteration_count", 0)
    }


# ================== Main ==================

if __name__ == "__main__":
    print("=" * 60)
    print("LangGraph MAS Proof-of-Concept")
    print("=" * 60)
    
    if not LANGGRAPH_AVAILABLE:
        print("\n⚠️  LangGraph not installed!")
        print("Run: pip install langgraph langchain langchain-openai")
        exit(1)
    
    print("\n✓ LangGraph available")
    
    # Test cases
    test_tasks = [
        {"id": "1", "type": "research_analysis", "payload": {"species": "Psilocybe cubensis"}},
        {"id": "2", "type": "security_scan", "payload": {"target": "api"}},
        {"id": "3", "type": "technical_review", "payload": {"component": "mindex"}},
    ]
    
    for task in test_tasks:
        print(f"\n--- Task {task['id']}: {task['type']} ---")
        result = run_task(task, f"session-{task['id']}")
        print(f"Agents: {' → '.join(result['agents_executed'])}")
        print(f"Iterations: {result['iterations']}")
    
    print("\n" + "=" * 60)
    print("✓ Proof-of-concept complete")
    print("See docs/LANGGRAPH_EVALUATION_REPORT.md for full analysis")

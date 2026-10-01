from langgraph.graph import StateGraph, START, END
from app.agent_state import AgentState
from app.nodes import (
    planner_node,
    llm_reasoning_node,
    tool_executor_node,
    force_finalize_node,
    MAX_ITERATIONS,
)


def route_entry(state: AgentState) -> str:
    return "planner" if state.get("plan") is None else "llm_reasoning"


def after_llm_reasoning(state: AgentState) -> str:
    plan = state.get("plan") or []
    step_index = state.get("current_step_index", 0)
    mid_plan = bool(plan) and step_index < len(plan)

    if state["current_tool_call"] is None:
        if mid_plan:
            return "force_finalize" if state["iteration_count"] >= MAX_ITERATIONS else "nudge"
        return "end"
    return "continue"


def after_tool_executor(state: AgentState) -> str:
    if state.get("awaiting_confirmation"):
        return "checkpoint"
    return "force_finalize" if state["iteration_count"] >= MAX_ITERATIONS else "continue"


graph = StateGraph(AgentState)
graph.add_node("Planner", planner_node)
graph.add_node("LLM_Reasoning", llm_reasoning_node)
graph.add_node("Tool_Executor", tool_executor_node)
graph.add_node("Force_Finalize", force_finalize_node)

graph.add_conditional_edges(START, route_entry, {"planner": "Planner", "llm_reasoning": "LLM_Reasoning"})
graph.add_edge("Planner", END)
graph.add_conditional_edges(
    "LLM_Reasoning", after_llm_reasoning,
    {"continue": "Tool_Executor", "end": END, "nudge": "LLM_Reasoning", "force_finalize": "Force_Finalize"},
)
graph.add_conditional_edges(
    "Tool_Executor", after_tool_executor,
    {"continue": "LLM_Reasoning", "force_finalize": "Force_Finalize", "checkpoint": END},
)
graph.add_edge("Force_Finalize", END)

agent_graph = graph.compile()
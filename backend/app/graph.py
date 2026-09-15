from langgraph.graph import StateGraph, END
from app.agent_state import AgentState
from app.nodes import llm_reasoning_node, tool_executor_node, force_finalize_node, MAX_ITERATIONS

def after_llm_reasoning(state: AgentState) -> str:
    return "end" if state["current_tool_call"] is None else "continue"


def after_tool_executor(state: AgentState) -> str:
    return "force_finalize" if state["iteration_count"] >= MAX_ITERATIONS else "continue"

graph = StateGraph(AgentState)
graph.add_node("LLM_Reasoning", llm_reasoning_node)
graph.add_node("Tool_Executor", tool_executor_node)
graph.add_node("Force_Finalize", force_finalize_node)

graph.set_entry_point("LLM_Reasoning")
graph.add_conditional_edges(
    "LLM_Reasoning", after_llm_reasoning, {"continue": "Tool_Executor", "end": END}
)
graph.add_conditional_edges(
    "Tool_Executor", after_tool_executor, {"continue": "LLM_Reasoning", "force_finalize": "Force_Finalize"}
)
graph.add_edge("Force_Finalize", END)

agent_graph = graph.compile()
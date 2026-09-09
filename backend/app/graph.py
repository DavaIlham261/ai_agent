from langgraph.graph import StateGraph, END
from app.agent_state import AgentState
from app.nodes import llm_reasoningg_node, tool_executor_node, MAX_ITERATIONS

def should_continue(state:AgentState) -> str:
    # Force Stop: iterations count mencapai maksimal
    if state["iteration_count"] >= MAX_ITERATIONS:
        return "end"
    
    # Sukses: LLM tidak meminta tool lagi
    if state["current_tool_call"] is None:
        return "end"
    
    return "continue"

graph = StateGraph(AgentState)
graph.add_node("LLM_Reasoning", llm_reasoningg_node, next_node=should_continue)
graph.add_node("Tool_Executor", tool_executor_node, next_node=should_continue)

graph.set_entry_point("LLM_Reasoning")
graph.add_conditional_edges(
    "LLM_Reasoning",
    should_continue,
    {"continue": "Tool_Executor", "end": END}
)
graph.add_edge("Tool_Executor", "LLM_Reasoning")

agent_graph = graph.compile()

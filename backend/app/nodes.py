

from langchain_core.messages import AIMessage, ToolMessage
from app.agent_state import AgentState


MAX_ITERATIONS = 5

# Dummy tool
def dummy_echo_tool(text: str) -> str:
    return f"Echo: {text}"

TOOLS = {"dummy_echo_tool": dummy_echo_tool}

def llm_reasoningg_node(state: AgentState) -> dict:
    """Node LLM_Reasoning: sementaea pakai logika dummy, nanti diganti Via LiteLLM"""
    last_message = state["messages"][-1]
    
    # Dummy logic: kalau pesan terakhir dari user (belum pernah panggil tool),
    # 'pura-pura' minta tool call. Kalau sudah dapat ToolMessage, selesai.
    if isinstance(last_message, ToolMessage):
        ai_msg = AIMessage(content=f"Selesai. Hasil Tool: {last_message.content}")
        return {"messages": [ai_msg], "current_tool_call": None}
    
    tool_call = {"name": "dummy_echo_tool", "args": {"text": last_message.content}}
    ai_msg = AIMessage(content="", tool_call=[
        {"id": "call_1", "name":tool_call["name"], "args": tool_call["args"]}
    ])
    return {"messages": [ai_msg], "current_tool_call": tool_call}

def tool_executor_node(state: AgentState) -> dict:
    """Node Tool_Executor: eksekusi tool + error recovery (SKPL 5.3)"""
    tool_call = state["current_tool_call"]
    try:
        func = TOOLS[tool_call["name"]]
        result = func(**tool_call["args"])
        tool_msg = ToolMessage(content=str(result), tool_call_id="call_1")
    except Exception as e:
        tool_msg = ToolMessage(
            content=f"Error: {str(e)}", tool_call_id="call_1"
        )
    
    return {
        "messages" : [tool_msg],
        "iteration_count": state["iteration_count"] + 1,
    }

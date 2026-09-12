import json
import os

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from openai import AsyncOpenAI

from app.agent_state import AgentState
from app.mcp_client import call_mcp_tool

MAX_ITERATIONS = 5

client = AsyncOpenAI(
    base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4000"),
    api_key=os.getenv("LITELLM_MASTER_KEY"),
)
MODEL_NAME = os.getenv("LITELLM_MODEL", "groq-llama-3.3-70b")


def _to_openai_messages(messages):
    result = []
    for m in messages:
        if isinstance(m, HumanMessage):
            result.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            entry = {"role": "assistant", "content": m.content or ""}
            if m.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])},
                    }
                    for tc in m.tool_calls
                ]
            result.append(entry)
        elif isinstance(m, ToolMessage):
            result.append(
                {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content}
            )
    return result


async def llm_reasoning_node(state: AgentState, config: RunnableConfig) -> dict:
    tools_schema = config["configurable"]["tools_schema"]

    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=_to_openai_messages(state["messages"]),
        tools=tools_schema,
    )
    choice = response.choices[0].message

    if choice.tool_calls:
        tc = choice.tool_calls[0]
        tool_call = {"name": tc.function.name, "args": json.loads(tc.function.arguments)}
        ai_msg = AIMessage(
            content=choice.content or "",
            tool_calls=[{"id": tc.id, "name": tc.function.name, "args": tool_call["args"]}],
        )
        return {"messages": [ai_msg], "current_tool_call": tool_call}

    ai_msg = AIMessage(content=choice.content or "")
    return {"messages": [ai_msg], "current_tool_call": None}


async def tool_executor_node(state: AgentState, config: RunnableConfig) -> dict:
    project = config["configurable"]["project"]
    project_id = config["configurable"]["project_id"]

    tool_call = state["current_tool_call"]
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]

    tool_args = dict(tool_call["args"])
    if tool_call["name"] in ("write_file", "patch_file"):
        # session_id perlu ikut supaya pesan commit git sesuai SKPL-F06
        tool_args["session_id"] = config["configurable"].get("session_id", "unknown")

    # MCPUnreachableError SENGAJA tidak ditangkap di sini -> dibiarkan menjalar
    # ke endpoint FastAPI, supaya langsung jadi error response yang jelas (SKPL-NF07),
    # bukan diam-diam masuk lagi ke LLM_Reasoning.
    result_text = await call_mcp_tool(project, project_id, tool_call["name"], tool_args)

    tool_msg = ToolMessage(content=result_text, tool_call_id=tool_call_id)
    return {
        "messages": [tool_msg],
        "iteration_count": state["iteration_count"] + 1,
    }
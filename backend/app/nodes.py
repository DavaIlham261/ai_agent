import json
import os

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from openai import OpenAI

from app.agent_state import AgentState

MAX_ITERATIONS = 5

client = OpenAI(
    base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4000"),
    api_key=os.getenv("LITELLM_MASTER_KEY"),
)
MODEL_NAME = os.getenv("LITELLM_MODEL", "groq-llama-3.3-70b")


def dummy_echo_tool(text: str) -> str:
    return f"echo: {text}"


TOOLS = {"dummy_echo_tool": dummy_echo_tool}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "dummy_echo_tool",
            "description": "Mengembalikan teks yang sama persis seperti input. Dipakai untuk uji coba tool-calling.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    }
]


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


def llm_reasoning_node(state: AgentState) -> dict:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=_to_openai_messages(state["messages"]),
        tools=TOOLS_SCHEMA,
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


def tool_executor_node(state: AgentState) -> dict:
    tool_call = state["current_tool_call"]
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    try:
        func = TOOLS[tool_call["name"]]
        result = func(**tool_call["args"])
        tool_msg = ToolMessage(content=str(result), tool_call_id=tool_call_id)
    except Exception as e:
        tool_msg = ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_call_id)

    return {
        "messages": [tool_msg],
        "iteration_count": state["iteration_count"] + 1,
    }
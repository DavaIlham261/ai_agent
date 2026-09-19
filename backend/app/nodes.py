import asyncio
import json
import os
import logging
import time

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from openai import AsyncOpenAI

from app.agent_state import AgentState
from app.mcp_client import call_mcp_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent")

MAX_ITERATIONS = 12
LLM_CALL_TIMEOUT_SECONDS = 30
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
MODEL_NAME = os.getenv("LITELLM_MODEL", "groq-llama-3.3-70b")

SYSTEM_PROMPT = (
    "Kamu adalah AI coding agent otonom. Kalau diminta membuat file besar "
    "(misal HTML/CSS lengkap), JANGAN coba tulis semuanya sekaligus lewat write_file "
    "dalam satu panggilan. Pecah jadi beberapa bagian logis (misal: head+navbar, "
    "hero section, konten utama, footer) dan tulis bertahap: gunakan write_file "
    "untuk bagian pertama, lalu append_file berulang kali untuk bagian berikutnya."
)


client = AsyncOpenAI(
    base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4000"),
    api_key=os.getenv("LITELLM_MASTER_KEY"),
)


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

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + _to_openai_messages(state["messages"])
    t0 = time.monotonic()
    
    response = await asyncio.wait_for(
        client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools_schema,
            max_tokens=MAX_TOKENS,
        ),
        timeout=LLM_CALL_TIMEOUT_SECONDS
    )
    
    elapsed = time.monotonic() - t0

    choice = response.choices[0]
    logger.info(
        "LLM_Reasoning | iterasi=%s | finish_reason=%s | waktu=%.1fs",
        state["iteration_count"], choice.finish_reason, elapsed,
    )

    if choice.message.tool_calls:
        tc = choice.message.tool_calls[0]
        tool_call = {"name": tc.function.name, "args": json.loads(tc.function.arguments)}
        ai_msg = AIMessage(
            content=choice.message.content or "",
            tool_calls=[{"id": tc.id, "name": tc.function.name, "args": tool_call["args"]}],
        )
        return {"messages": [ai_msg], "current_tool_call": tool_call}

    if choice.finish_reason == "length":
        logger.warning("Jawaban KEHABISAN TOKEN (finish_reason=length) pada iterasi=%s", state["iteration_count"])

    ai_msg = AIMessage(content=choice.message.content or "")
    return {"messages": [ai_msg], "current_tool_call": None}

async def tool_executor_node(state: AgentState, config: RunnableConfig) -> dict:
    project = config["configurable"]["project"]
    project_id = config["configurable"]["project_id"]

    tool_call = state["current_tool_call"]
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]

    tool_args = dict(tool_call["args"])
    if tool_call["name"] in ("write_file", "patch_file", "append_file"):
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
    
async def force_finalize_node(state: AgentState, config: RunnableConfig) -> dict:
    logger.warning("Force_Finalize DIPICU | iterasi_terakhir=%s", state["iteration_count"])

    messages = _to_openai_messages(state["messages"])
    messages.append({
        "role": "user",
        "content": (
            "Batas maksimal langkah tercapai. Berikan jawaban akhir berdasarkan "
            "informasi yang sudah kamu kumpulkan sejauh ini, tanpa memanggil tool lagi."
        ),
    })
    response = await client.chat.completions.create(model=MODEL_NAME, messages=messages, max_tokens=MAX_TOKENS)
    choice = response.choices[0]
    logger.info("Force_Finalize selesai | finish_reason=%s", choice.finish_reason)

    content = choice.message.content or "(Batas iterasi tercapai, tidak ada jawaban tersedia.)"
    return {"messages": [AIMessage(content=content)], "current_tool_call": None}
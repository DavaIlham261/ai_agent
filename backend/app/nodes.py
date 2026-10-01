import json
import os
import logging
import time

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from openai import AsyncOpenAI, BadRequestError
import asyncio

from app.agent_state import AgentState
from app.mcp_client import call_mcp_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent")

class NodeTimeoutError(Exception):
    """Timeout di SATU node/langkah — beda dari timeout total (asyncio.TimeoutError biasa)."""
    pass


MAX_ITERATIONS = 12
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
LLM_CALL_TIMEOUT_SECONDS = 45

client = AsyncOpenAI(
    base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4000"),
    api_key=os.getenv("LITELLM_MASTER_KEY"),
)
MODEL_NAME = os.getenv("LITELLM_MODEL", "agent-model")

SYSTEM_PROMPT = (
    "Kamu adalah AI coding agent otonom. ATURAN WAJIB: setiap kali memanggil write_file "
    "atau append_file, isi parameter 'content' MAKSIMAL sekitar 1500 karakter per panggilan. "
    "Untuk file besar (HTML/CSS/JS lengkap), WAJIB pecah jadi beberapa bagian logis dan tulis "
    "bertahap: write_file untuk bagian pertama (PENDEK), lalu append_file berulang kali untuk "
    "bagian-bagian berikutnya. JANGAN PERNAH mencoba menulis konten panjang dalam satu panggilan."
)

PLANNER_SYSTEM_PROMPT = (
    "Kamu adalah perencana tugas untuk AI coding agent. Pecah permintaan user jadi "
    "langkah-langkah konkret dan berurutan. Jawab HANYA dengan JSON array of object, "
    "tanpa teks lain, tanpa markdown code block. Tiap object: "
    '{"description": "...", "confirm_after": true/false}. '
    "confirm_after=true HANYA untuk langkah yang menandai selesainya satu FASE besar yang "
    "layak dicek user sebelum lanjut (misal: setelah HTML+CSS selesai, sebelum mulai JS). "
    "Langkah kecil dalam fase yang sama pakai confirm_after=false supaya lanjut otomatis "
    "tanpa menunggu user. Buat 3-6 langkah. Contoh: "
    '[{"description": "Buat index.html struktur dasar", "confirm_after": false}, '
    '{"description": "Buat style.css lengkap", "confirm_after": true}, '
    '{"description": "Buat script.js interaktivitas", "confirm_after": false}]'
)

# Tool "lokal" — bukan dari MCP, ditangani langsung di tool_executor_node,
# supaya LLM punya cara eksplisit bilang "langkah ini selesai".
LOCAL_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "mark_step_complete",
            "description": (
                "Panggil ini SETELAH langkah saat ini di rencana benar-benar selesai, "
                "sebelum mulai langkah berikutnya. Jangan panggil tool lain bersamaan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "catatan": {"type": "string", "description": "Ringkasan singkat apa yang sudah dikerjakan."}
                },
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


async def planner_node(state: AgentState, config: RunnableConfig) -> dict:
    user_request = state["messages"][-1].content

    response = await asyncio.wait_for(
        client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": user_request},
            ],
            max_tokens=MAX_TOKENS,
        ),
        timeout=LLM_CALL_TIMEOUT_SECONDS,
    )
    raw = response.choices[0].message.content or "[]"

    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, list) or not parsed:
            raise ValueError
        plan = [
            {
                "description": str(item.get("description", item)) if isinstance(item, dict) else str(item),
                "confirm_after": bool(item.get("confirm_after", False)) if isinstance(item, dict) else False,
            }
            for item in parsed
        ]
    except (json.JSONDecodeError, ValueError, AttributeError):
        plan = [{"description": user_request, "confirm_after": False}]

    plan_text = "\n".join(
        f"{i + 1}. {step['description']}" + (" ⏸️ (jeda konfirmasi)" if step["confirm_after"] else "")
        for i, step in enumerate(plan)
    )
    reply = (
        f"Rencana pengerjaan:\n\n{plan_text}\n\n"
        "Balas 'lanjut' untuk mulai — setelah ini agen jalan otomatis sampai titik jeda "
        "berikutnya, tidak perlu ketik 'lanjut' tiap langkah kecil."
    )
    return {
        "messages": [AIMessage(content=reply)],
        "plan": plan,
        "current_step_index": 0,
        "current_tool_call": None,
        "awaiting_confirmation": False,
    }

async def llm_reasoning_node(state: AgentState, config: RunnableConfig) -> dict:
    tools_schema = config["configurable"]["tools_schema"]

    plan = state.get("plan") or []
    step_index = state.get("current_step_index", 0)
    if plan and step_index < len(plan):
        step_reminder = (
            f"Rencana keseluruhan: {[s['description'] for s in plan]}. "
            f"Kamu sedang di langkah ke-{step_index + 1}: \"{plan[step_index]['description']}\". "
            "Fokus selesaikan langkah ini dulu. Kalau sudah selesai, panggil tool "
            "mark_step_complete sebelum lanjut ke langkah berikutnya."
        )
    else:
        step_reminder = "Semua langkah rencana sudah selesai. Berikan ringkasan akhir untuk user."
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += _to_openai_messages(state["messages"])
    messages.append({"role": "system", "content": step_reminder})

    t0 = time.monotonic()
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=MODEL_NAME, messages=messages, tools=tools_schema, max_tokens=MAX_TOKENS,
            ),
            timeout=LLM_CALL_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - t0
        logger.warning(
            "LLM_Reasoning TIMEOUT | iterasi=%s | elapsed=%.1fs (batas %ss)",
            state["iteration_count"], elapsed, LLM_CALL_TIMEOUT_SECONDS,
        )
        raise NodeTimeoutError(f"LLM_Reasoning timeout pada iterasi {state['iteration_count']}") from None
    except BadRequestError as e:
        logger.warning("Argumen tool gagal di-generate (kemungkinan konten kepanjangan): %s", e)
        corrective_messages = messages + [{
            "role": "system",
            "content": (
                "PERINGATAN: Panggilan tool sebelumnya GAGAL karena argumen konten terlalu "
                "panjang sehingga tidak valid. WAJIB pecah konten jadi bagian JAUH lebih kecil "
                "(maksimal ~800 karakter kali ini). Gunakan write_file untuk bagian pertama yang "
                "PENDEK, lalu append_file berkali-kali untuk sisanya."
            ),
        }]
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=MODEL_NAME, messages=corrective_messages, tools=tools_schema, max_tokens=MAX_TOKENS,
                ),
                timeout=LLM_CALL_TIMEOUT_SECONDS,
            )
        except (asyncio.TimeoutError, BadRequestError) as e2:
            logger.error("Retry setelah kegagalan argumen JSON juga gagal: %s", e2)
            return {
                "messages": [AIMessage(
                    content="Maaf, gagal menghasilkan konten karena terlalu panjang untuk sekali generate. "
                            "Coba minta bagian yang lebih kecil, atau lanjutkan langkah ini lagi."
                )],
                "current_tool_call": None,
            }

    elapsed = time.monotonic() - t0

    choice = response.choices[0]
    message = choice.message
    logger.info(
        "LLM_Reasoning | iterasi=%s | finish_reason=%s | waktu=%.1fs",
        state["iteration_count"], choice.finish_reason, elapsed,
    )

    if message.tool_calls:
        tc = message.tool_calls[0]
        tool_call = {"name": tc.function.name, "args": json.loads(tc.function.arguments)}
        ai_msg = AIMessage(
            content=message.content or "",
            tool_calls=[{"id": tc.id, "name": tc.function.name, "args": tool_call["args"]}],
        )
        return {"messages": [ai_msg], "current_tool_call": tool_call}

    if choice.finish_reason == "length":
        logger.warning("Jawaban KEHABISAN TOKEN (finish_reason=length) pada iterasi=%s", state["iteration_count"])

    ai_msg = AIMessage(content=message.content or "")
    mid_plan = bool(plan) and step_index < len(plan)
    if mid_plan:
        # masih di tengah rencana tapi LLM cuma narasi tanpa tool -> jangan dianggap selesai,
        # tapi tetap makan jatah iterasi supaya tidak bisa nyangkut selamanya
        return {
            "messages": [ai_msg],
            "current_tool_call": None,
            "iteration_count": state["iteration_count"] + 1,
        }
    return {"messages": [ai_msg], "current_tool_call": None}


async def tool_executor_node(state: AgentState, config: RunnableConfig) -> dict:
    tool_call = state["current_tool_call"]
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]

    if tool_call["name"] == "mark_step_complete":
        plan = state.get("plan") or []
        old_index = state.get("current_step_index", 0)
        new_index = old_index + 1
        note = tool_call["args"].get("catatan", "")
        just_finished = plan[old_index] if old_index < len(plan) else {}
        needs_checkpoint = bool(just_finished.get("confirm_after"))

        if new_index >= len(plan):
            content = f"Langkah selesai: {note}. Semua langkah rencana sudah selesai."
        elif needs_checkpoint:
            content = (
                f"Langkah selesai: {note}. Ini titik jeda — menunggu konfirmasi kamu "
                f"sebelum lanjut ke: {plan[new_index]['description']}"
            )
        else:
            content = f"Langkah selesai: {note}. Lanjut otomatis ke: {plan[new_index]['description']}"

        tool_msg = ToolMessage(content=content, tool_call_id=tool_call_id)
        return {
            "messages": [tool_msg],
            "iteration_count": state["iteration_count"] + 1,
            "current_step_index": new_index,
            "awaiting_confirmation": needs_checkpoint,
        }

    project = config["configurable"]["project"]
    project_id = config["configurable"]["project_id"]

    tool_args = dict(tool_call["args"])
    if tool_call["name"] in ("write_file", "patch_file", "append_file"):
        tool_args["session_id"] = config["configurable"].get("session_id", "unknown")

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
    response = await asyncio.wait_for(
        client.chat.completions.create(model=MODEL_NAME, messages=messages, max_tokens=MAX_TOKENS),
        timeout=LLM_CALL_TIMEOUT_SECONDS,
    )
    content = response.choices[0].message.content or "(Batas iterasi tercapai, tidak ada jawaban tersedia.)"
    return {"messages": [AIMessage(content=content)], "current_tool_call": None}
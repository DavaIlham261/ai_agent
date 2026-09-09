import json
import os

import redis
from dotenv import load_dotenv
from langchain_core.messages import messages_from_dict, messages_to_dict

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL_SECONDS = 24 * 60 * 60  # 24 hours

r = redis.from_url(REDIS_URL, decode_responses=True)

def load_session(session_id: str) -> dict | None:
    raw = r.get(f"session:{session_id}")
    if raw is None: return None
    data = json.loads(raw)
    
    return {
        "messages": messages_from_dict(data["messages"]),
        "iteration_count": data["iteration_count"],
        "current_tool_call": data["current_tool_call"],
    }

def save_session(session_id:str, state: dict) -> None:
    payload = json.dumps({
        "messages": messages_to_dict(state["messages"]),
        "iteration_count": state["iteration_count"],
        "current_tool_call": state["current_tool_call"],
    })
    r.set(f"session:{session_id}", payload, ex=SESSION_TTL_SECONDS)
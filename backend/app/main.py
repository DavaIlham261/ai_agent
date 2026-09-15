import asyncio
import httpx
import os
import logging
import time
from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, ToolMessage
from app.mcp_client import fetch_mcp_tools, MCPUnreachableError

from app.auth import verify_api_key
from app.graph import agent_graph
from app.redis_client import load_session, save_session
from app.projects import PROJECTS, get_project
from app.mcp_client import fetch_mcp_tools, MCPUnreachableError

logger = logging.getLogger("agent")
app = FastAPI(title="AI Agent Backend", description="Backend API for AI Agent", version="1.0.0")


class AgentRunRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)

class AgentRunResponse(BaseModel):
    session_id: str
    status: str
    response: str
    execution_steps: list[str]


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()}
    )

LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "http://localhost:4000")


async def check_litellm() -> str:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{LITELLM_BASE_URL}/health/liveliness")
        return "ok" if resp.status_code == 200 else "unreachable"
    except Exception:
        return "unreachable"


async def check_mcp_server(project_id: str, project: dict) -> str:
    try:
        await fetch_mcp_tools(project, project_id)
        return "ok"
    except MCPUnreachableError:
        return "unreachable"


@app.get("/health")
async def health_check():
    litellm_status = await check_litellm()

    mcp_results = await asyncio.gather(
        *[check_mcp_server(pid, p) for pid, p in PROJECTS.items()]
    )
    mcp_status = dict(zip(PROJECTS.keys(), mcp_results))

    return {"api": "ok", "litellm": litellm_status, "mcp_servers": mcp_status}

@app.post(
    "/api/v1/agent/run",
    response_model=AgentRunResponse,
    dependencies=[Depends(verify_api_key)]
)
async def run_agent(payload: AgentRunRequest):
    project = get_project(payload.project_id)
    if project is None:
        raise HTTPException(
            status_code=400,
            detail=f"project_id tidak terdaftar: {payload.project_id}",
        )
    
    try:
        tools_schema = await fetch_mcp_tools(project, payload.project_id)
    except MCPUnreachableError as e:
        raise HTTPException(status_code=502, detail=str(e))

    existing = load_session(payload.session_id)
    if existing:
        initial_state = existing
        initial_state["messages"].append(HumanMessage(content=payload.prompt))
    else:
        initial_state = {
            "messages": [HumanMessage(content=payload.prompt)],
            "iteration_count": 0,
            "current_tool_call": None,
        }

    run_config = {
        "configurable": {
            "tools_schema": tools_schema,
            "project": project,
            "project_id": payload.project_id,
            "session_id": payload.session_id,
        }
    }

    t0 = time.monotonic()
    try:
        final_state = await asyncio.wait_for(
            agent_graph.ainvoke(initial_state, config=run_config),
            timeout=60,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "TIMEOUT SKPL-F01 | session=%s | elapsed=%.1fs", payload.session_id, time.monotonic() - t0
        )
        raise HTTPException(status_code=504, detail="Agent execution timed out")
    except MCPUnreachableError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")
    
    logger.info(
        "Request selesai | session=%s | elapsed=%.1fs | iterasi_akhir=%s",
        payload.session_id, time.monotonic() - t0, final_state["iteration_count"],
    )

    
    save_session(payload.session_id, final_state)
    
    execution_steps = [
        m.content for m in final_state["messages"] if isinstance(m, ToolMessage)
    ]
    
    final_answer = final_state["messages"][-1].content
    
    return AgentRunResponse(
        session_id=payload.session_id,
        status="success",
        response=final_answer,
        execution_steps=execution_steps
    )
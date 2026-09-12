import asyncio
from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, ToolMessage
from app.mcp_client import fetch_mcp_tools, MCPUnreachableError

from app.auth import verify_api_key
from app.graph import agent_graph
from app.redis_client import load_session, save_session
from app.projects import get_project

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


@app.get("/health")
async def health_check():
    return {"status": "OK"}

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

    try:
        final_state = await asyncio.wait_for(
            agent_graph.ainvoke(initial_state, config=run_config),
            timeout=60,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Agent execution timed out")
    except MCPUnreachableError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")
    
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
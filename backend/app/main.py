import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, ToolMessage

from app.graph import agent_graph

app = FastAPI(title="AI Agent Backend", description="Backend API for AI Agent", version="1.0.0")


class AgentRunRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)

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

@app.post("/api/v1/agent/run", response_model=AgentRunResponse)
async def run_agent(payload: AgentRunRequest):

    initial_state = {
        "messages": [HumanMessage(content=payload.prompt)],
        "iteration_count": 0,
        "current_tool_call": None,
    }
    
    try:
        final_state = await asyncio.wait_for(
            asyncio.to_thread(agent_graph.invoke, initial_state),
            timeout=60
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Agent execution timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
    
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
from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    iteration_count: int
    current_tool_call: dict | None
    plan: list[str] | None
    current_step_index: int
    awaiting_confirmation: bool
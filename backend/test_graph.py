from app.graph import agent_graph
from langchain_core.messages import HumanMessage

initial_state = {
    "messages": [HumanMessage(content="Halo agen")],
    "iteration_count": 0,
    "current_tool_call": None,
}

final_state = agent_graph.invoke(initial_state)
for m in final_state["messages"]:
    print(type(m).__name__, "-", m.content)
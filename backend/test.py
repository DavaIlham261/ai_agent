import json
from langchain_core.messages import HumanMessage
from app.nodes import client, MODEL_NAME, TOOLS_SCHEMA, _to_openai_messages

messages = [HumanMessage(content="gunakan tool dummy_echo_tool untuk mengulangi kata halo dunia")]

payload = _to_openai_messages(messages)
print("=== Payload messages yang dikirim ===")
print(json.dumps(payload, indent=2, ensure_ascii=False))
print("=== Model ===", MODEL_NAME)

response = client.chat.completions.create(
    model=MODEL_NAME,
    messages=payload,
    tools=TOOLS_SCHEMA,
)
print("=== Response ===")
print(response)
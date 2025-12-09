from langgraph.types import StreamWriter
from app.lib.graph.state import State


async def receive_message(state: State, writer: StreamWriter):
    """Passthrough node that ensures input messages are checkpointed"""
    print(f"=== receive_message node ===")
    print(f"Messages count: {len(state['messages'])}")
    for i, msg in enumerate(state["messages"]):
        print(f"  [{i}] {msg.__class__.__name__}: {msg.content[:50]}...")

    return {"messages": state["messages"]}

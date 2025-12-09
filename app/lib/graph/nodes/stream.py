from langgraph.types import StreamWriter

from app.lib.graph.state import State


async def stream_final_response(state: State, writer: StreamWriter):
    """Stream the validated response to the user"""
    pending = state.get("pending_response", "")

    if not pending:
        print("Warning: No pending response to stream")
        return {}

    print(f"Streaming final response ({len(pending)} chars)")

    chunk_size = 4
    for i in range(0, len(pending), chunk_size):
        chunk = pending[i : i + chunk_size]
        writer(chunk)

    return {}

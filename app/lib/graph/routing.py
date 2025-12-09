from langgraph.types import Send

from app.lib.graph.state import State


def dispatch_sources(state: State):
    """Route to appropriate search nodes based on classification"""
    tasks = []
    if state.get("needs_visa_api"):
        tasks.append(Send("visa_search", state))

    if state.get("needs_web_search"):
        tasks.append(Send("web_search", state))

    if state.get("needs_rag"):
        tasks.append(Send("rag_search", state))

    if not tasks:
        return Send("generate_response", state)

    return tasks


def should_retry_or_stream(state: State):
    """Decide whether to retry generation or stream the final response"""
    retry_count = state.get("retry_count", 0)
    relevance_passed = state.get("relevance_passed", False)

    if relevance_passed:
        return "stream"

    if retry_count >= 5:
        print("Max retries reached, streaming best attempt")
        return "stream"

    return "retry"

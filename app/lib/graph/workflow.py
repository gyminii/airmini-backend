from langgraph.graph import StateGraph, START, END

from app.lib.graph.state import State
from app.lib.graph.nodes import (
    receive_message,
    classify_query,
    web_search,
    rag_search,
    visa_search,
    generate_response,
    relevance_check,
    stream_final_response,
)
from app.lib.graph.routing import dispatch_sources, should_retry_or_stream


def build_workflow() -> StateGraph:
    """Build and return the chat workflow graph"""
    workflow = StateGraph(State)

    workflow.add_node("receive_message", receive_message)
    workflow.add_node("classify", classify_query)
    workflow.add_node("visa_search", visa_search)
    workflow.add_node("web_search", web_search)
    workflow.add_node("rag_search", rag_search)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("relevance_check", relevance_check)
    workflow.add_node("stream_response", stream_final_response)

    workflow.add_edge(START, "receive_message")
    workflow.add_edge("receive_message", "classify")
    workflow.add_conditional_edges("classify", dispatch_sources)

    # All search nodes lead to generate_response
    workflow.add_edge("visa_search", "generate_response")
    workflow.add_edge("web_search", "generate_response")
    workflow.add_edge("rag_search", "generate_response")

    # Generate → Relevance check
    workflow.add_edge("generate_response", "relevance_check")

    # After relevance check: retry or stream
    workflow.add_conditional_edges(
        "relevance_check",
        should_retry_or_stream,
        {
            "stream": "stream_response",
            "retry": "classify",
        },
    )

    # Stream → End
    workflow.add_edge("stream_response", END)

    return workflow


workflow = build_workflow()

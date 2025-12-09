from typing import TypedDict, Annotated, Optional, Dict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.database.models import TripContext


def merge_sources(existing: list[str], new: list[str]) -> list[str]:
    if new == []:
        return []
    combined = existing + new
    seen = set()
    result = []
    for item in combined:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    trip_context: Optional[TripContext]

    # question and its type
    query: Optional[str]
    query_type: Optional[str]

    needs_visa_api: bool
    needs_web_search: bool
    needs_rag: bool

    sources_used: Annotated[list[str], merge_sources]

    relevance_passed: bool
    retry_count: int

    # results container for each method
    rag_results: Optional[list[dict]]
    web_results: Optional[Dict]
    visa_results: Optional[Dict]

    # pending response for streaming after validation
    pending_response: Optional[str]

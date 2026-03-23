from langgraph.types import StreamWriter

from app.lib.graph.state import State
from app.lib.rag import (
    retrieve_web_results,
    retrieve_rag_results,
    retrieve_visa_requirements,
)


async def web_search(state: State, writer: StreamWriter):
    writer({"type": "thought", "content": "Searching the web...", "phase": "search"})

    query = state.get("query")
    trip_context = state.get("trip_context")
    results = await retrieve_web_results(query, trip_context=trip_context)
    if results:
        count = len(results.get("results", []))
        writer(
            {
                "type": "thought",
                "content": f"Found {count} web results",
                "phase": "search",
            }
        )

    return {
        "sources_used": ["web"],
        "web_results": results,
    }


async def rag_search(state: State, writer: StreamWriter):
    writer({"type": "thought", "content": "Searching knowledge base...", "phase": "knowledge"})

    query = state["query"]
    trip_context = state.get("trip_context")
    results = await retrieve_rag_results(query, trip_context=trip_context)

    if results:
        writer({"type": "thought", "content": f"Found {len(results)} relevant documents", "phase": "knowledge"})
        return {"sources_used": ["rag"], "rag_results": results}

    # No KB results — fall back to web search
    writer({"type": "thought", "content": "No KB matches, searching the web...", "phase": "search"})
    trip_context = state.get("trip_context")
    web_results = await retrieve_web_results(query, trip_context=trip_context)
    count = len(web_results.get("results", [])) if web_results else 0
    writer({"type": "thought", "content": f"Found {count} web results", "phase": "search"})
    return {
        "sources_used": ["rag", "web"],
        "rag_results": [],
        "web_results": web_results,
    }


async def visa_search(state: State, writer: StreamWriter):
    writer(
        {"type": "thought", "content": "Checking visa requirements...", "phase": "visa"}
    )

    trip_context = state.get("trip_context")

    has_nationality = trip_context and trip_context.get("nationality_country_code")
    has_destination = trip_context and trip_context.get("destination_country_code")

    if not has_nationality or not has_destination:
        missing = []
        if not has_nationality:
            missing.append("passport country")
        if not has_destination:
            missing.append("destination")

        writer(
            {
                "type": "thought",
                "content": f"Need more info: {', '.join(missing)}",
                "phase": "visa",
            }
        )

        return {
            "sources_used": ["visa"],
            "visa_results": {
                "status": "incomplete",
                "missing_fields": missing,
                "message": f"To check visa requirements, I need to know your {' and '.join(missing)}.",
            },
        }

    result = await retrieve_visa_requirements(trip_context)

    if result:
        writer(
            {
                "type": "thought",
                "content": "Visa information retrieved",
                "phase": "visa",
            }
        )
    else:
        writer(
            {
                "type": "thought",
                "content": "Could not retrieve visa info for this route",
                "phase": "visa",
            }
        )

    return {
        "sources_used": ["visa"],
        "visa_results": result,
    }

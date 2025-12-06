from typing import TypedDict, Annotated, Optional, List, Dict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages

from app.config import get_settings
from app.database.models import TripContext
from app.lib.llm import chat_model
from app.lib.rag.retriever import (
    retrieve_web_results,
    retrieve_rag_results,
    retrieve_visa_requirements,
    format_rag_sources,
    format_web_sources,
    format_visa_sources,
)
import json
from langgraph.types import Send, StreamWriter


settings = get_settings()


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


# setting the title before moving further.
async def generate_chat_title(message: str) -> str:
    """Generate a concise title from the first user message"""
    prompt = f"""
    Generate a short, descriptive title (max 6 words) for a chat that starts with this message:
    "{message}"
    
    Return ONLY the title, no quotes, no explanation.
    Examples:
    - "What are TSA liquid rules?" → "TSA Liquid Rules"
    - "Do I need a visa to Japan?" → "Japan Visa Requirements"
    - "Help me pack for Paris" → "Paris Packing Guide"
    """

    response = chat_model.invoke([HumanMessage(content=prompt)])
    title = response.content.strip().strip('"').strip("'")
    return title[:60]


"""Figure out what kind of question this is"""


async def classify_query(state: State, writer: StreamWriter):
    last_message = state["messages"][-1].content
    retry_count = state.get("retry_count", 0)
    previous_sources = state.get("sources_used", [])

    writer({"type": "thought", "content": "Analyzing your question..."})
    retry_hint = ""
    if retry_count > 0:
        retry_hint = f"""
        RETRY ATTEMPT {retry_count}: Previous answer was insufficient.
        Sources already tried: {previous_sources}
        Try to be MORE COMPREHENSIVE - consider if additional sources would help.
        """

    prompt = f"""
    You are analyzing a travel question. Determine what information sources are needed.

    Question: {last_message}
    {retry_hint}

    Respond with ONLY the raw JSON object. Do NOT use markdown code blocks, backticks, or any formatting.
    Your response must be ONLY valid JSON that can be directly parsed.

    Format:
    {{
        "query_type": "general",
        "needs_visa_api": false,
        "needs_web_search": false,
        "needs_rag": false
    }}

    Rules:
    - If asking about visa requirements, entry requirements → needs_visa_api: true
    - If asking about security/TSA/baggage rules for USA, Canada, or South Korea → needs_rag: true
    - If asking about security/TSA/baggage rules for OTHER countries → needs_web_search: true
    - If asking about GENERAL travel topics (liquids, carry-on, prohibited items) → needs_rag: true
    - If asking about current news, flights, weather → needs_web_search: true
    - For complex questions, multiple sources may be needed

    query_type can be: "visa", "general", "security", "baggage", "customs", "weather", "country_specific"

    IMPORTANT: Output ONLY the JSON object with no markdown formatting.
    """

    response = chat_model.invoke([HumanMessage(content=prompt)])

    # Strip markdown code blocks if present
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    print(f"Classification response (retry {retry_count}): {content}")

    try:
        result = json.loads(content)
        return {
            "query": last_message,
            "query_type": result["query_type"],
            "needs_visa_api": result.get("needs_visa_api", False),
            "needs_web_search": result.get("needs_web_search", False),
            "needs_rag": result.get("needs_rag", False),
            "sources_used": [],  # Reset for new attempt
        }
    except json.JSONDecodeError:
        print(f"Failed to parse: {response.content}")
        return {
            "query": last_message,
            "query_type": "general",
            "needs_visa_api": False,
            "needs_web_search": False,
            "needs_rag": False,
            "sources_used": [],
        }


def dispatch_sources(state: State):
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


async def web_search(state: State, writer: StreamWriter):
    writer({"type": "thought", "content": "Searching the web..."})

    query = state.get("query")
    results = await retrieve_web_results(query)
    if results:
        count = len(results.get("results", []))
        writer({"type": "thought", "content": f"Found {count} web results"})

    return {
        "sources_used": ["web"],
        "web_results": results,
    }


async def rag_search(state: State, writer: StreamWriter):
    writer({"type": "thought", "content": "Searching knowledge base..."})
    query = state["query"]
    results = await retrieve_rag_results(query)
    writer({"type": "thought", "content": f"Found {len(results)} relevant documents"})

    return {
        "sources_used": ["rag"],
        "rag_results": results,
    }


async def visa_search(state: State, writer: StreamWriter):
    writer({"type": "thought", "content": "Checking visa requirements..."})
    trip_context = state.get("trip_context")
    result = await retrieve_visa_requirements(trip_context)

    if result:
        writer({"type": "thought", "content": "Visa information retrieved"})
    else:
        writer(
            {
                "type": "thought",
                "content": "Visa check unavailable (missing trip details)",
            }
        )
    return {
        "sources_used": ["visa"],
        "visa_results": result,
    }


async def generate_response(state: State, writer: StreamWriter):
    print(f"Generating response using sources: {state['sources_used']}")

    sources_data = []
    if "rag" in state["sources_used"]:
        rag_result = state.get("rag_results")
        sources_data.extend(format_rag_sources(rag_result))

    if "web" in state["sources_used"]:
        web_result = state.get("web_results")
        sources_data.extend(format_web_sources(web_result))

    if "visa" in state["sources_used"]:
        visa_results = state.get("visa_results")
        sources_data.extend(format_visa_sources(visa_results))

    # Build the messages list with conversation history
    messages = []

    # System message
    system_content = """You are Airmini, a helpful travel assistant specializing in:
        - Visa and immigration requirements
        - Flight information and airline policies
        - TSA/security regulations and baggage rules
        - Travel tips and destination information
        - Customs and entry requirements

        IMPORTANT RULES:
        1. Remember details the user has shared (like their name, travel plans, etc.)
        2. For off-topic questions unrelated to travel/aviation (like coding, math, recipes, etc.), politely redirect:
        "I'm Airmini, your travel assistant! I can help with visa requirements, flight info, baggage rules, and travel tips. What travel questions can I help you with?"
        3. For casual greetings or personal info (like "my name is X"), respond naturally and remember it.
        4. Be direct, helpful, and conversational."""

    if sources_data:
        system_content += f"""

Available information from {', '.join(state['sources_used'])} sources:
{chr(10).join(sources_data)}

Use these sources to provide accurate information when relevant."""

    messages.append({"role": "system", "content": system_content})

    # Add conversation history
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})

    chunks: list[str] = []

    async for chunk in chat_model.astream(messages):
        text = ""

        if hasattr(chunk, "content"):
            if isinstance(chunk.content, str):
                text = chunk.content
            elif isinstance(chunk.content, list):
                text = "".join(
                    part.get("text", "")
                    for part in chunk.content
                    if isinstance(part, dict) and part.get("type") == "text"
                )

        if not text:
            continue

        writer(text)
        chunks.append(text)

    full_text = "".join(chunks)

    ai_msg = AIMessage(content=full_text)
    return {"messages": [ai_msg]}


async def receive_message(state: State, writer: StreamWriter):
    """Passthrough node that ensures input messages are checkpointed"""
    print(f"=== receive_message node ===")
    print(f"Messages count: {len(state['messages'])}")
    for i, msg in enumerate(state["messages"]):
        print(f"  [{i}] {msg.__class__.__name__}: {msg.content[:50]}...")

    # Return the messages so they get saved by checkpointer
    return {"messages": state["messages"]}


async def relevance_check(state: State, writer: StreamWriter):
    """Check if the gathered information is relevant and sufficient"""
    writer({"type": "thought", "content": "Checking answer quality..."})
    retry_count = state.get("retry_count", 0)
    print(f"Checking relevance (attempt {retry_count + 1}/5)")

    last_ai_message = state.get("messages")[-1].content
    query = state.get("query")

    prompt = f"""
        Evaluate if this response appropriately addresses the user's message.
        
        User's message: {query}
        Assistant's response: {last_ai_message}
        
        Criteria:
        1. If the user asked a travel-related question: Does the response answer it?
        2. If the user shared personal info (like their name): Does the response acknowledge it?
        3. If the user asked something off-topic: Does the response politely redirect to travel topics?
        4. For greetings/casual chat: Is the response friendly and appropriate?
        
        A response that politely redirects off-topic questions IS a valid response.
        
        Respond with ONLY valid JSON (no markdown, no code blocks):
        {{"relevance_passed": true, "reason": "brief explanation"}}
        OR
        {{"relevance_passed": false, "reason": "what's missing"}}
        """

    response = chat_model.invoke([HumanMessage(content=prompt)])

    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        result = json.loads(content)
        passed = result.get("relevance_passed", False)
        reason = result.get("reason", "")
        print(f"   Relevance: {'PASSED' if passed else 'FAILED'} - {reason}")

        if not passed:
            writer(
                {
                    "type": "thought",
                    "content": f"Answer insufficient: {reason}. Searching again...",
                }
            )
        else:
            writer({"type": "thought", "content": "Answer quality verified"})

        return {"relevance_passed": passed, "retry_count": retry_count + 1}

    except json.JSONDecodeError:
        print(f"   Failed to parse relevance response: {content[:100]}")
        writer(
            {
                "type": "thought",
                "content": "Could not verify quality, proceeding anyway",
            }
        )
        return {"relevance_passed": True, "retry_count": retry_count + 1}


def should_retry_search(state: State):
    retry_count = state.get("retry_count", 0)
    relevance_passed = state.get("relevance_passed", False)

    if relevance_passed or retry_count >= 5:
        if retry_count >= 5 and not relevance_passed:
            print("Max retries reached, returning best attempt")
        return "end"

    return "retry"


workflow = StateGraph(State)
workflow.add_node("receive_message", receive_message)
workflow.add_node("classify", classify_query)
workflow.add_node("visa_search", visa_search)
workflow.add_node("web_search", web_search)
workflow.add_node("rag_search", rag_search)
workflow.add_node("generate_response", generate_response)
workflow.add_node("relevance_check", relevance_check)

workflow.add_edge(START, "receive_message")  # Start here
workflow.add_edge("receive_message", "classify")
workflow.add_conditional_edges("classify", dispatch_sources)

workflow.add_edge("visa_search", "generate_response")
workflow.add_edge("web_search", "generate_response")
workflow.add_edge("rag_search", "generate_response")

workflow.add_edge("generate_response", "relevance_check")

workflow.add_conditional_edges(
    "relevance_check", should_retry_search, {"end": END, "retry": "classify"}
)

if __name__ == "__main__":
    import asyncio
    from app.lib.provider import get_graph

    async def test():
        test_state = {
            "messages": [HumanMessage(content="What are TSA Gun Rules?")],
            "trip_context": None,
            "query": None,
            "query_type": None,
            "needs_visa_api": False,
            "needs_web_search": False,
            "needs_rag": False,
            "rag_results": None,
            "web_results": None,
            "visa_results": None,
            "sources_used": [],
            "relevance_passed": False,
            "retry_count": 0,
        }
        graph = get_graph()
        result = await graph.ainvoke(
            test_state,
            config={"configurable": {"thread_id": "test-123"}},
        )

        print(f"\n{'='*50}")
        print(f"Query type: {result.get('query_type')}")
        print(f"Sources used: {result.get('sources_used')}")
        print(f"Relevance passed: {result.get('relevance_passed')}")
        print(f"Retry count: {result.get('retry_count')}")
        print(f"Final answer: {result['messages'][-1].content}")
        print(f"{'='*50}")

    asyncio.run(test())

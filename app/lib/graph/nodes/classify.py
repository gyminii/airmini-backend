import json
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import StreamWriter

from app.lib.llm import chat_model
from app.lib.graph.state import State


def _build_conversation_context(messages: list, last_n_pairs: int = 3) -> str:
    """Extract the last N human/AI exchanges for classifier context."""
    exchanges = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            exchanges.append(f"User: {content[:300]}")
        elif isinstance(msg, AIMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            exchanges.append(f"Assistant: {content[:300]}")

    # Take the last N pairs (each pair = 2 items), excluding the very last user message
    # (that's the current query, already shown separately)
    recent = exchanges[-(last_n_pairs * 2 + 1):-1]
    return "\n".join(recent) if recent else ""


async def classify_query(state: State, writer: StreamWriter):
    """Figure out what kind of question this is"""

    retry_count = state.get("retry_count", 0)
    previous_sources = state.get("sources_used", [])
    trip_context = state.get("trip_context")

    # On first attempt, extract from last human message
    # On retries, reuse the stored query
    if retry_count == 0:
        last_human_message = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                last_human_message = msg.content
                break
        query = last_human_message or ""
    else:
        query = state.get("query", "")

    if not query:
        print("Warning: No query found")
        return {
            "query": "",
            "query_type": "general",
            "needs_visa_api": False,
            "needs_web_search": False,
            "needs_rag": False,
            "sources_used": [],
        }

    writer(
        {
            "type": "thought",
            "content": (
                "Analyzing your question..."
                if retry_count == 0
                else "Trying different approach..."
            ),
            "phase": "analysis",
        }
    )

    retry_hint = ""
    if retry_count > 0:
        retry_hint = f"""
        RETRY ATTEMPT {retry_count}: Previous answer was insufficient.
        Sources already tried: {previous_sources}
        Try to be MORE COMPREHENSIVE - consider if additional sources would help.
        """

    trip_context_section = ""
    if trip_context:
        trip_context_section = f"""
    
    USER'S TRIP CONTEXT (use this to better understand their question):
    - Nationality: {trip_context.get('nationality_country_code') or 'Not specified'}
    - Origin: {trip_context.get('origin_city_or_airport') or 'Not specified'}
    - Destination: {trip_context.get('destination_city_or_airport') or 'Not specified'}
    - Departure: {trip_context.get('departure_date') or 'Not specified'}
    - Return: {trip_context.get('return_date') or 'Not specified'}
    - Trip Type: {trip_context.get('trip_type') or 'Not specified'}
    - Purpose: {trip_context.get('purpose') or 'Not specified'}
    
    IMPORTANT: If the user has provided nationality and destination, questions about 
    "do I need a visa", "entry requirements", "documents needed" should trigger needs_visa_api: true.
    """

    conversation_context = _build_conversation_context(state["messages"])
    conversation_section = ""
    if conversation_context:
        conversation_section = f"""
    RECENT CONVERSATION (use this to understand follow-up questions):
{conversation_context}
    """

    prompt = f"""
    You are analyzing a travel question. Determine what information sources are needed.

    Current question: {query}
    {conversation_section}
    {trip_context_section}
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
    - If asking about visa requirements, entry requirements, documents needed → needs_visa_api: true
    - If user has trip context with nationality + destination and asks about entry/visa → needs_visa_api: true
    - If asking about security/TSA/baggage rules for USA, Canada, or South Korea → needs_rag: true
    - If asking about security/TSA/baggage rules for OTHER countries → needs_web_search: true
    - If asking about GENERAL travel topics (liquids, carry-on, prohibited items) → needs_rag: true
    - If asking about current news, flights, weather, prices → needs_web_search: true
    - For complex questions, multiple sources may be needed

    EDGE CASES TO HANDLE:
    - "Can I bring X?" → needs_rag (security/baggage rules)
    - "How long can I stay?" → needs_visa_api (visa duration)
    - "Do I need to quarantine?" → needs_web_search (current policies change)
    - "What's the weather like?" → needs_web_search (real-time data)
    - "Is it safe to travel to X?" → needs_web_search (current events)
    - "What vaccines do I need?" → needs_web_search (health requirements change)
    - "How early should I arrive?" → needs_rag (airport procedures)
    - "Transit visa" or "layover" questions → needs_visa_api
    - Currency, tipping, local customs → needs_web_search
    - Questions mentioning specific airlines → needs_web_search (airline-specific policies)
    
    IMPLICIT QUESTIONS (user has trip context):
    - "What do I need?" → If destination exists, likely asking about visa/entry requirements
    - "Am I allowed?" → Could be visa or security depending on context
    - "Any restrictions?" → Check both visa and current travel advisories

    FOLLOW-UP QUESTIONS: If the current question is vague ("Tell me more", "What are the alternatives?",
    "Any other options?", "What about X?") look at the recent conversation to understand what topic
    it refers to, then classify based on that topic. Never redirect a follow-up as off-topic if the
    prior conversation was travel-related.

    query_type can be: "visa", "general", "security", "baggage", "customs", "weather", "health", "transit", "country_specific"

    IMPORTANT: Output ONLY the JSON object with no markdown formatting.
    """

    response = await chat_model.ainvoke([HumanMessage(content=prompt)])

    raw = response.content
    content = (raw if isinstance(raw, str) else " ".join(str(p) for p in raw)).strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    print(f"Classification response (retry {retry_count}): {content}")

    try:
        result = json.loads(content)
        return {
            "query": query,
            "query_type": result["query_type"],
            "needs_visa_api": result.get("needs_visa_api", False),
            "needs_web_search": result.get("needs_web_search", False),
            "needs_rag": result.get("needs_rag", False),
            "sources_used": [],
        }
    except json.JSONDecodeError:
        print(f"Failed to parse: {content[:100]}")
        return {
            "query": query,
            "query_type": "general",
            "needs_visa_api": False,
            "needs_web_search": True,
            "needs_rag": False,
            "sources_used": [],
        }

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import StreamWriter

from app.lib.llm import chat_model
from app.lib.graph.state import State
from app.lib.rag import (
    format_rag_sources,
    format_web_sources,
    format_visa_sources,
)


def build_response_messages(state: State) -> list[dict]:
    """Build the messages list for LLM response generation"""
    trip_context = state.get("trip_context")

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

    messages = []

    trip_context_section = ""
    if trip_context:
        ctx_parts = []
        if trip_context.get("nationality_country_code"):
            ctx_parts.append(f"Passport: {trip_context['nationality_country_code']}")
        if trip_context.get("origin_city_or_airport"):
            ctx_parts.append(f"From: {trip_context['origin_city_or_airport']}")
        if trip_context.get("destination_city_or_airport"):
            ctx_parts.append(f"To: {trip_context['destination_city_or_airport']}")
        if trip_context.get("departure_date"):
            ctx_parts.append(f"Departure: {trip_context['departure_date']}")
        if trip_context.get("return_date"):
            ctx_parts.append(f"Return: {trip_context['return_date']}")
        if trip_context.get("purpose"):
            ctx_parts.append(f"Purpose: {trip_context['purpose']}")

        if ctx_parts:
            trip_context_section = f"""

USER'S TRIP DETAILS:
{chr(10).join(f'- {part}' for part in ctx_parts)}

Use these details to personalize your responses. For example:
- If they ask about visas, use their nationality and destination
- If they ask about flights, reference their origin/destination
- If they mention "my trip" or "my flight", you know their travel plans
- Proactively mention relevant info based on their trip
"""

    answer_language = "English"
    if trip_context and trip_context.get("answer_language") == "KO":
        answer_language = "Korean"

    system_content = f"""You are Airmini, a helpful travel assistant specializing in:
- Visa and immigration requirements
- Flight information and airline policies
- TSA/security regulations and baggage rules
- Travel tips and destination information
- Customs and entry requirements
{trip_context_section}
RESPONSE LANGUAGE: Respond in {answer_language}.

IMPORTANT RULES:
1. Remember details the user has shared (like their name, travel plans, etc.)
2. If trip context is provided, USE IT to give personalized answers
3. For off-topic questions unrelated to travel/aviation, politely redirect:
   "I'm Airmini, your travel assistant! I can help with visa requirements, flight info, baggage rules, and travel tips. What travel questions can I help you with?"
4. For casual greetings or personal info, respond naturally and remember it.
5. Be direct, helpful, and conversational.
6. When answering questions, naturally incorporate the user's trip details when relevant.

EDGE CASES TO HANDLE:
- If information might be outdated or change frequently (COVID rules, visa policies), add a brief disclaimer like "Policies may change - verify with official sources before travel."
- If sources conflict, mention the discrepancy and recommend checking official sources.
- If you don't have enough info to answer accurately, ask clarifying questions rather than guessing.
- For visa questions without nationality/destination, ask the user to provide their passport country and destination.
- For time-sensitive questions (flights, weather), note that info may not be real-time.
- If user asks about a specific airline but no airline_code in context, ask which airline.

NEVER:
- Make up visa requirements or entry rules
- Guarantee entry to any country (final decision is always with immigration)
- Provide medical or legal advice beyond general travel health/document info
- Assume nationality or destination if not provided - ask instead"""

    if sources_data:
        system_content += f"""

Available information from {', '.join(state['sources_used'])} sources:
{chr(10).join(sources_data)}

Use these sources to provide accurate information when relevant."""

    messages.append({"role": "system", "content": system_content})

    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})

    return messages


async def generate_response(state: State, writer: StreamWriter):
    """Generate response WITHOUT streaming - for validation"""
    retry_count = state.get("retry_count", 0)
    print(
        f"Generating response using sources: {state['sources_used']} (attempt {retry_count + 1})"
    )

    messages = build_response_messages(state)

    # Non-streaming generation for validation
    response = await chat_model.ainvoke(messages)

    full_text = ""
    if hasattr(response, "content"):
        if isinstance(response.content, str):
            full_text = response.content
        elif isinstance(response.content, list):
            full_text = "".join(
                part.get("text", "")
                for part in response.content
                if isinstance(part, dict) and part.get("type") == "text"
            )

    ai_msg = AIMessage(content=full_text)
    return {
        "messages": [ai_msg],
        "pending_response": full_text,
    }

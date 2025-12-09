import json
from langchain_core.messages import HumanMessage
from langgraph.types import StreamWriter

from app.lib.llm import chat_model
from app.lib.graph.state import State


async def relevance_check(state: State, writer: StreamWriter):
    """Check if the generated response is relevant and sufficient"""
    retry_count = state.get("retry_count", 0)
    trip_context = state.get("trip_context")
    sources_used = state.get("sources_used", [])

    print(f"Checking relevance (attempt {retry_count + 1}/5)")

    last_ai_response = state.get("pending_response", "")
    query = state.get("query")

    if not last_ai_response:
        print("No response to check")
        return {"relevance_passed": False, "retry_count": retry_count + 1}

    # If we've already retried with the same sources, don't keep trying
    if retry_count >= 2:
        print(
            f"   Already tried {retry_count} times with sources: {sources_used}, accepting response"
        )
        writer(
            {
                "type": "thought",
                "content": "Proceeding with best available information",
                "phase": "validation",
            }
        )
        return {"relevance_passed": True, "retry_count": retry_count + 1}

    trip_context_hint = ""
    if trip_context:
        ctx_parts = []
        if trip_context.get("nationality_country_code"):
            ctx_parts.append(f"Nationality: {trip_context['nationality_country_code']}")
        if trip_context.get("destination_city_or_airport"):
            ctx_parts.append(
                f"Destination: {trip_context['destination_city_or_airport']}"
            )
        if ctx_parts:
            trip_context_hint = f"""
    
    User's trip context: {', '.join(ctx_parts)}
    If the question relates to their trip, the response should use this context.
    """

    prompt = f"""
        Evaluate if this response appropriately addresses the user's message.
        
        User's message: {query}
        Assistant's response: {last_ai_response}
        {trip_context_hint}
        
        Criteria:
        1. If the user asked a travel-related question: Does the response answer it reasonably?
        2. If trip context was provided: Does the response use it when relevant?
        3. If the user shared personal info (like their name): Does the response acknowledge it?
        4. If the user asked something OFF-TOPIC (not travel related): Does the response politely redirect? THIS IS VALID.
        5. For greetings/casual chat: Is the response friendly and appropriate?
        
        VALID responses (should PASS):
        - Politely redirecting off-topic questions to travel topics
        - Asking for clarification
        - Adding disclaimers about checking official sources
        - Saying "I don't have real-time data" and providing what's available
        - Providing best-effort answers with caveats about data freshness
        - Any reasonable attempt to answer the question, even if imperfect
        
        INVALID responses (should FAIL):
        - Completely ignoring the user's question
        - Making up information without any source
        - Giving a totally unrelated response
        
        BE LENIENT: If the response makes a reasonable attempt to answer, even if the data isn't perfect, pass it.
        Weather data may be forecasts or slightly dated - this is acceptable with a disclaimer.
        
        Respond with ONLY valid JSON:
        {{"relevance_passed": true, "reason": "brief explanation"}}
        OR
        {{"relevance_passed": false, "reason": "what's wrong"}}
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
                    "content": "Refining answer...",
                    "phase": "validation",
                }
            )
        else:
            writer(
                {
                    "type": "thought",
                    "content": "Answer verified",
                    "phase": "validation",
                }
            )

        return {"relevance_passed": passed, "retry_count": retry_count + 1}

    except json.JSONDecodeError:
        print(f"   Failed to parse relevance response: {content[:100]}")
        writer(
            {
                "type": "thought",
                "content": "Proceeding with response",
                "phase": "validation",
            }
        )
        return {"relevance_passed": True, "retry_count": retry_count + 1}

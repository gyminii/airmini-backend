from typing import TypedDict, Annotated, Optional, List, Dict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages

from app.config import get_settings
from app.lib.api.visa import check_visa_requirements
from app.lib.api.web_search import search_web
from app.lib.rag.vectorstore import similarity_search
from app.database.models import TripContext
from app.lib.llm import chat_model
from langgraph.types import Send
import json

settings = get_settings()


def merge_sources(existing: list[str], new: list[str]) -> list[str]:
    if new == []:
        return []
    # Combine and deduplicate while preserving order
    combined = existing + new
    seen = set()
    result = []
    for item in combined:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


class State(TypedDict):
    # without add_messages fallback, it will replace the entire messages instead of
    # getting appended to the old list.
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


"""Figure out what kind of question this is"""


async def classify_query(state: State):
    last_message = state["messages"][-1].content
    retry_count = state.get("retry_count", 0)
    previous_sources = state.get("sources_used", [])

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


async def web_search(state: State):
    print("Search web node called")
    query = state.get("query")
    results = await search_web(query, 5)
    if results:
        print(f"   Found {len(results.get('results', []))} web results")

    return {
        "sources_used": ["web"],
        "web_results": results,
    }


async def rag_search(state: State):
    print("Rag search node called")

    query = state["query"]
    print(f" RAG search for: {query}")
    #  Searching through the vectordb
    results = await similarity_search(query, k=5, score_threshold=0.5)

    print(f" Found {len(results)} relevant documents")
    for i, result in enumerate(results, 1):
        print(f"   {i}. Score: {result['score']:.2f}")
        print(f"      Source: {result['source']}")
        print(f"      Content preview: {result['content'][:100]}...")
        print()

    return {
        "sources_used": ["rag"],
        "rag_results": results,
    }


async def visa_search(state: State):
    print("Visa Search node called")

    trip_context = state.get("trip_context")

    if (
        trip_context
        and trip_context.get("nationality_country_code")
        and trip_context.get("destination_country_code")
    ):
        passport_country = trip_context["nationality_country_code"]
        destination_country = trip_context["destination_country_code"]
        result = await check_visa_requirements(passport_country, destination_country)

        print(f"   Checked visa: {passport_country} → {destination_country}")

        return {
            "sources_used": ["visa"],
            "visa_results": result,
        }
    else:
        print("   Missing nationality or destination country for visa check")
        return {
            "sources_used": ["visa"],
            "visa_results": None,
        }


# Helper functions for formatting..
def format_rag_sources(rag_results: Optional[list[dict]]) -> list[str]:
    """Format RAG results for GPT context"""
    if not rag_results:
        return ["No relevant information in knowledge base."]

    formatted = ["=== Knowledge Base ==="]
    for i, result in enumerate(rag_results, 1):
        source = (
            result["source"].rsplit("/", 1)[-1]
            if "/" in result["source"]
            else result["source"]
        )
        formatted.append(f"\n[Source {i} - {source}]")
        formatted.append(result["content"])

    return formatted


def format_web_sources(web_results: Optional[Dict]) -> list[str]:
    """Format web search results for GPT context"""
    if not web_results:
        return ["Web search returned no results."]

    formatted = ["\n=== Web Search ==="]

    # Add Tavily's AI summary if available
    if web_results.get("answer"):
        formatted.append(f"Summary: {web_results['answer']}\n")

    # Add top 3 web results
    for i, result in enumerate(web_results.get("results", [])[:3], 1):
        formatted.append(f"[Result {i}] {result.get('title', 'Untitled')}")
        formatted.append(f"{result.get('content', '')[:300]}...\n")

    return formatted


def format_visa_sources(visa_results: Optional[Dict]) -> list[str]:
    """Format visa API results for GPT context"""
    if not visa_results:
        return ["Visa information not available."]

    formatted = ["\n=== Visa Requirements ==="]
    formatted.append(json.dumps(visa_results, indent=2))

    return formatted


async def generate_response(state: State):
    print(f"Generating response using sources: {state['sources_used']}")

    sources_data = []
    if "rag" in state["sources_used"]:
        sources_data.extend(format_rag_sources(state.get("rag_results")))

    if "web" in state["sources_used"]:
        sources_data.extend(format_web_sources(state.get("web_results")))

    if "visa" in state["sources_used"]:
        sources_data.extend(format_visa_sources(state.get("visa_results")))

    prompt = f"""
    User question: {state.get('query')}
    
    Available information from {', '.join(state['sources_used'])} sources:
    {chr(10).join(sources_data)}
    
    Based on the above sources, provide a helpful and accurate answer.
    Be direct, cite sources, and provide actionable information.
  """
    response = chat_model.invoke([HumanMessage(content=prompt)])
    return {"messages": [response]}


async def relevance_check(state: State):
    """Check if the gathered information is relevant and sufficient"""

    retry_count = state.get("retry_count", 0)
    print(f"Checking relevance (attempt {retry_count + 1}/5)")

    last_ai_message = state.get("messages")[-1].content
    query = state.get("query")

    prompt = f"""
    Evaluate if this response answers the user's question.
    
    User's question: {query}
    Assistant's response: {last_ai_message}
    
    Criteria:
    1. Does the response directly address what the user asked?
    2. Is the response specific enough to be helpful?
    3. Does it provide actionable information or clear next steps?
    
    Ignore whether sources are mentioned or if data is placeholder - focus ONLY on whether 
    the response structure and content type match what was asked.
    
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
        return {"relevance_passed": passed, "retry_count": retry_count + 1}
    except json.JSONDecodeError:
        print(f"   Failed to parse relevance response: {content[:100]}")
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
workflow.add_node("classify", classify_query)
workflow.add_node("visa_search", visa_search)
workflow.add_node("web_search", web_search)
workflow.add_node("rag_search", rag_search)
workflow.add_node("generate_response", generate_response)
workflow.add_node("relevance_check", relevance_check)

workflow.add_edge(START, "classify")
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

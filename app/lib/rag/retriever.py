from typing import Optional, Dict, List
from app.lib.api.visa import check_visa_requirements
from app.lib.api.web_search import search_web
from app.lib.rag.vectorstore import similarity_search
from app.database.models import TripContext


# web search
async def retrieve_web_results(query: str, num_results: int = 5) -> Optional[Dict]:
    """Retrieve web search results for a query"""
    print(f"Searching web for: {query}")
    results = await search_web(query, num_results)
    if results:
        print(f"   Found {len(results.get('results', []))} web results")
    return results


# rag search
async def retrieve_rag_results(
    query: str, k: int = 5, score_threshold: float = 0.5
) -> List[dict]:
    """Retrieve documents from vector store"""
    print(f"RAG search for: {query}")
    results = await similarity_search(query, k=k, score_threshold=score_threshold)
    print(f"   Found {len(results)} relevant documents")
    return results


# visa search (technically an api search so its also a web search)
async def retrieve_visa_requirements(
    trip_context: Optional[TripContext],
) -> Optional[Dict]:
    """Retrieve visa requirements based on trip context"""
    print("Checking visa requirements")

    if not trip_context:
        print("   No trip context provided")
        return None

    if hasattr(trip_context, "nationality_country_code"):
        passport_country = trip_context.nationality_country_code
        destination_country = trip_context.destination_country_code
    else:
        passport_country = trip_context.get("nationality_country_code")
        destination_country = trip_context.get("destination_country_code")

    if not passport_country or not destination_country:
        print("   Missing nationality or destination country")
        return None

    result = await check_visa_requirements(passport_country, destination_country)
    print(f"   Checked visa: {passport_country} → {destination_country}")
    return result


# Formatter functions
def format_rag_sources(rag_results: Optional[List[dict]]) -> List[str]:
    """Format RAG results for LLM context"""
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


def format_web_sources(web_results: Optional[Dict]) -> List[str]:
    """Format web search results for LLM context"""
    if not web_results:
        return ["Web search returned no results."]

    formatted = ["\n=== Web Search ==="]

    if web_results.get("answer"):
        formatted.append(f"Summary: {web_results['answer']}\n")

    for i, result in enumerate(web_results.get("results", [])[:3], 1):
        formatted.append(f"[Result {i}] {result.get('title', 'Untitled')}")
        formatted.append(f"{result.get('content', '')[:300]}...\n")

    return formatted


def format_visa_sources(visa_results: Optional[Dict]) -> List[str]:
    """Format visa API results for LLM context"""
    if not visa_results:
        return ["Visa information not available."]

    formatted = ["\n=== Visa Requirements ==="]
    import json

    formatted.append(json.dumps(visa_results, indent=2))

    return formatted

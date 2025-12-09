from typing import Optional, Dict, List

from app.lib.api.visa import check_visa_requirements
from app.lib.api.web_search import search_web
from app.lib.rag.vectorstore import similarity_search
from app.database.models import TripContext


async def retrieve_web_results(query: str, num_results: int = 5) -> Optional[Dict]:
    """Retrieve web search results for a query"""
    print(f"Searching web for: {query}")
    results = await search_web(query, num_results)
    if results:
        print(
            f" Web search success: '{query}' ({len(results.get('results', []))} results)"
        )
    return results


async def retrieve_rag_results(
    query: str,
    k: int = 5,
    score_threshold: float = 0.5,
) -> List[dict]:
    """Retrieve documents from vector store"""
    print(f"RAG search for: {query}")
    results = await similarity_search(query, k=k, score_threshold=score_threshold)
    print(f"   Found {len(results)} relevant documents")
    return results


async def retrieve_visa_requirements(
    trip_context: Optional[TripContext],
) -> Optional[Dict]:
    """Retrieve visa requirements based on trip context"""
    print("Checking visa requirements")

    if not trip_context:
        print("   No trip context provided")
        return None

    # Handle both object and dict access
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

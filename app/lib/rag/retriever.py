from typing import Optional, Dict, List

from app.lib.api.visa import check_visa_requirements
from app.lib.api.web_search import search_web
from app.lib.rag.vectorstore import similarity_search
from app.database.models import TripContext


def _enrich_query(query: str, trip_context: Optional[Dict]) -> str:
    """Append trip context to query for better search relevance"""
    if not trip_context:
        return query
    parts = []
    if trip_context.get("nationality_country_code"):
        parts.append(trip_context["nationality_country_code"])
    if trip_context.get("destination_country_code"):
        parts.append(trip_context["destination_country_code"])
    if not parts:
        return query
    return f"{query} {' '.join(parts)}"


async def retrieve_web_results(
    query: str, num_results: int = 5, trip_context: Optional[Dict] = None
) -> Optional[Dict]:
    """Retrieve web search results for a query"""
    enriched = _enrich_query(query, trip_context)
    print(f"Searching web for: {enriched}")
    return await search_web(enriched, num_results)


def _build_rag_filter(trip_context: Optional[Dict]) -> Optional[dict]:
    """Build a PGVector metadata filter from trip context when airline/country is known."""
    if not trip_context:
        return None
    airline = trip_context.get("airline_code")
    country = trip_context.get("destination_country_code")
    if airline:
        return {"airline_code": {"$eq": airline}}
    if country:
        return {"country_code": {"$eq": country}}
    return None


async def retrieve_rag_results(
    query: str,
    k: int = 5,
    score_threshold: float = 0.5,
    trip_context: Optional[Dict] = None,
) -> List[dict]:
    """Retrieve documents from vector store, optionally filtered by airline/country."""
    print(f"RAG search for: {query}")

    # Try filtered search first if we have context; fall back to unfiltered
    filter_meta = _build_rag_filter(trip_context)
    results = await similarity_search(
        query, k=k, score_threshold=score_threshold, filter_metadata=filter_meta
    )

    if not results and filter_meta:
        print(f"   No results with filter {filter_meta}, retrying without filter")
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

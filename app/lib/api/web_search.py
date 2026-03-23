from tavily import AsyncTavilyClient
from typing import Optional, List, Dict
from app.config import get_settings

settings = get_settings()

client = AsyncTavilyClient(api_key=settings['tavily_apikey'])


async def search_web(query: str, max_results: int = 5) -> Optional[Dict]:
    try:
        response = await client.search(
            query=query,
            max_results=max_results,
            search_depth='advanced',
            include_answer=True,
        )
        print(f" Web search success: '{query}' ({len(response.get('results', []))} results)")
        return {
            "results": response.get("results", []),
            "answer": response.get("answer", ""),
            "query": query,
        }
    except Exception as e:
        print(f" Web search exception: {e}")
        return None

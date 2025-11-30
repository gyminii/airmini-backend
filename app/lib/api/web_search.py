from tavily import TavilyClient
from typing import Optional, List, Dict
from app.config import get_settings

settings = get_settings()

client = TavilyClient(
  api_key=settings['tavily_apikey']
)

async def search_web(query: str, max_results: int = 5) -> Optional[List[Dict]]:
  try:
    response = client.search(
      query=query,
      max_results=max_results,
      search_depth='advanced',
      include_answer=True
    )
    print(f" Web search success: '{query}' ({len(response.get('results', []))} results)")
    return {
            "results": response.get("results", []),
            "answer": response.get("answer", ""),
            "query": query
        }
  except Exception as e:
    print(f" Web search exception: {e}")
    return None

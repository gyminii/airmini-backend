from langchain_core.documents import Document
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from .core import normalize_text, text_splitter


async def _extract_with_tavily(url: str) -> str:
    """Fallback: extract content via Tavily Extract API"""
    from tavily import AsyncTavilyClient
    from app.config import get_settings

    settings = get_settings()
    client = AsyncTavilyClient(api_key=settings["tavily_apikey"])
    response = await client.extract(urls=[url])
    results = response.get("results", [])
    if not results or not results[0].get("raw_content"):
        raise ValueError("Tavily Extract returned no content")
    return results[0]["raw_content"]


async def ingest_url(url: str, extra_metadata: dict | None = None) -> dict:
    """Ingest a web URL into chunks. Falls back to Tavily Extract for JS-heavy sites."""
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    crawler_config = CrawlerRunConfig(
        wait_until="domcontentloaded",
        page_timeout=30000,
        delay_before_return_html=5.0,
        js_code=[
            "window.scrollTo(0, document.body.scrollHeight);",
            "await new Promise(r => setTimeout(r, 2000));",
            """
            const selectorsToRemove = [
                'header', 'footer', 'nav', 'iframe',
                '[class*="cookie"]', '[class*="modal"]',
                '[class*="popup"]', '[class*="logout"]'
            ];
            selectorsToRemove.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => el.remove());
            });
            """,
        ],
    )

    content = None
    crawl_error = None

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=crawler_config)

            if result.success:
                raw = result.markdown or result.cleaned_html or result.html
                if raw and len(raw.strip()) >= 100:
                    content = normalize_text(raw)
            else:
                crawl_error = result.error_message
    except Exception as e:
        crawl_error = str(e)

    if not content:
        print(f"   crawl4ai failed ({crawl_error}), trying Tavily Extract...")
        try:
            raw = await _extract_with_tavily(url)
            content = normalize_text(raw)
            print(f"   Tavily Extract succeeded ({len(content)} chars)")
        except Exception as e:
            raise ValueError(
                f"Both crawl4ai and Tavily Extract failed for {url}. "
                f"crawl4ai: {crawl_error} | Tavily: {e}"
            )

    base_metadata = {"source": url, "type": "web"}
    if extra_metadata:
        base_metadata.update(extra_metadata)

    document = Document(page_content=content, metadata=base_metadata)
    chunks = text_splitter.split_documents([document])

    texts = [chunk.page_content for chunk in chunks]
    metadatas = [dict(base_metadata) for _ in chunks]

    return {"texts": texts, "metadatas": metadatas}

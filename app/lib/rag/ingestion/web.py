from langchain_core.documents import Document
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from app.lib.rag.config import redundancy_filter
from .core import normalize_text, text_splitter


async def ingest_url(url: str) -> dict:
    """Ingest a web URL into chunks"""
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

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=crawler_config)

        if not result.success:
            raise ValueError(f"Crawl failed: {result.error_message}")

        content = result.markdown or result.cleaned_html or result.html

        if not content or len(content.strip()) < 100:
            raise ValueError(f"Insufficient content: {len(content)} chars")

        content = normalize_text(content)

    document = Document(
        page_content=content,
        metadata={"source": url, "type": "web"},
    )
    chunks = text_splitter.split_documents([document])
    filtered_chunks = await redundancy_filter.atransform_documents(chunks)

    texts = [chunk.page_content for chunk in filtered_chunks]
    metadatas = [{"source": url, "type": "web"} for _ in filtered_chunks]

    return {"texts": texts, "metadatas": metadatas}

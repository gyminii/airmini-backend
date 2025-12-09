from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from app.lib.rag.vectorstore import add_documents
from cleantext import clean
from langchain_core.documents import Document
from app.lib.rag.vectorstore import remove_redundancy
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


# ingestion.py
def normalize_page_content(text: str) -> str:
    return clean(
        text,
        clean_all=False,
        extra_spaces=True,
        stemming=False,
        stopwords=False,
        lowercase=False,
        numbers=False,
        punct=False,
        reg="",  # no regex
        reg_replace="",  # no regex replacement
        stp_lang="english",
    )


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ".", " ", ""],
)


async def ingest_pdf(file_path: str) -> dict:

    try:
        from langchain_community.document_loaders import UnstructuredPDFLoader
    except ImportError as e:
        raise RuntimeError(
            "UnstructuredPDFLoader requires the 'ingestion'"
            "(unstructured[docx,pdf]) to be installed. "
            "Run: uv sync --group ingestion"
        ) from e
    loader = UnstructuredPDFLoader(file_path, strategy="hi_res")
    documents = loader.load()

    for doc in documents:
        doc.page_content = normalize_page_content(doc.page_content)

    chunks = text_splitter.split_documents(documents)
    filtered_chunks = await remove_redundancy.atransform_documents(chunks)

    texts = [chunk.page_content for chunk in filtered_chunks]
    metadatas = [
        {"source": file_path, "type": "pdf", "page": chunk.metadata.get("page", 0)}
        for chunk in filtered_chunks
    ]

    return {"texts": texts, "metadatas": metadatas}


async def ingest_url(url: str) -> dict:
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

        content = normalize_page_content(content)

    document = Document(page_content=content, metadata={"source": url, "type": "web"})
    chunks = text_splitter.split_documents([document])
    filtered_chunks = await remove_redundancy.atransform_documents(chunks)

    texts = [chunk.page_content for chunk in filtered_chunks]
    metadatas = [{"source": url, "type": "web"} for chunk in filtered_chunks]

    return {"texts": texts, "metadatas": metadatas}


async def ingest_text_file(file_path: str) -> dict:
    loader = TextLoader(file_path)
    documents = loader.load()

    for doc in documents:
        doc.page_content = normalize_page_content(doc.page_content)

    chunks = text_splitter.split_documents(documents)
    filtered_chunks = await remove_redundancy.atransform_documents(chunks)

    texts = [chunk.page_content for chunk in filtered_chunks]
    metadatas = [{"source": file_path, "type": "text"} for chunk in filtered_chunks]

    return {"texts": texts, "metadatas": metadatas}


async def ingest_documents_batch(sources: list[dict]):
    all_texts = []
    all_metadatas = []

    for source in sources:
        print(
            f"Processing {source.get('type')}: {source.get('path') or source.get('url')}"
        )
        source_type = source["type"]

        try:
            if source_type == "pdf":
                result = await ingest_pdf(source["path"])
            elif source_type == "url":
                result = await ingest_url(source["url"])
            elif source_type == "text":
                result = await ingest_text_file(source["path"])
            else:
                print(f"Unknown type: {source['type']}")
                continue

            all_texts.extend(result["texts"])
            all_metadatas.extend(result["metadatas"])
            print(f"   Created {len(result['texts'])} chunks")

        except Exception as e:
            print(f"   Error: {e}")
            continue

    if all_texts:
        await add_documents(all_texts, all_metadatas)
        print(f"\nTotal: {len(all_texts)} chunks ingested")
    else:
        print("\nNo documents processed")

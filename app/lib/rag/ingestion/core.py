import asyncio
from datetime import datetime, timezone

from cleantext import clean
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.lib.rag.vectorstore import add_documents, get_ingested_sources


def normalize_text(text: str) -> str:
    """Normalize text content for ingestion"""
    return clean(
        text,
        clean_all=False,
        extra_spaces=True,
        stemming=False,
        stopwords=False,
        lowercase=False,
        numbers=False,
        punct=False,
        reg="",
        reg_replace="",
        stp_lang="english",
    )


# Shared text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ".", " ", ""],
)


async def ingest_documents_batch(sources: list[dict]):
    """Batch ingest multiple document sources with dedup and parallel processing"""
    from app.lib.rag.ingestion import ingest_text_file, ingest_url, ingest_pdf

    # Skip sources already in the vector store
    existing = await get_ingested_sources()
    new_sources = []
    for source in sources:
        key = source.get("url") or source.get("path", "")
        if key in existing:
            print(f"Skipping (already ingested): {key}")
        else:
            new_sources.append(source)

    if not new_sources:
        print("All sources already ingested — nothing to do")
        return

    print(f"Ingesting {len(new_sources)} new sources ({len(sources) - len(new_sources)} skipped)")

    semaphore = asyncio.Semaphore(5)

    async def process_source(source: dict):
        async with semaphore:
            key = source.get("url") or source.get("path", "")
            print(f"Processing {source.get('type')}: {key}")

            # Build extra metadata from source definition (airline_code, country_code, etc.)
            reserved = {"type", "url", "path"}
            extra = {k: v for k, v in source.items() if k not in reserved}
            extra["ingested_at"] = datetime.now(timezone.utc).isoformat()

            try:
                if source["type"] == "pdf":
                    result = await ingest_pdf(source["path"], extra_metadata=extra)
                elif source["type"] == "url":
                    result = await ingest_url(source["url"], extra_metadata=extra)
                elif source["type"] == "text":
                    result = await ingest_text_file(source["path"], extra_metadata=extra)
                else:
                    print(f"Unknown type: {source['type']}")
                    return None
                print(f"   {len(result['texts'])} chunks from {key}")
                return result
            except Exception as e:
                print(f"   Error on {key}: {e}")
                return None

    batch_results = await asyncio.gather(*[process_source(s) for s in new_sources])

    all_texts = []
    all_metadatas = []
    for result in batch_results:
        if result:
            all_texts.extend(result["texts"])
            all_metadatas.extend(result["metadatas"])

    if all_texts:
        await add_documents(all_texts, all_metadatas)
        print(f"\nTotal: {len(all_texts)} chunks ingested")
    else:
        print("\nNo new documents processed")

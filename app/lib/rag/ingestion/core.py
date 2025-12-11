from cleantext import clean
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.lib.rag.vectorstore import add_documents


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
    """Batch ingest multiple document sources"""

    from app.lib.rag.ingestion import ingest_text_file, ingest_url, ingest_pdf

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

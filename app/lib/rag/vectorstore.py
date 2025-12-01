import asyncio
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from app.config import get_settings
from langchain_community.document_transformers import EmbeddingsRedundantFilter

settings = get_settings()

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small", api_key=settings["openai_apikey"]
)


connection_string = settings["database_url"]

vector_store = PGVector(
    embeddings=embeddings,
    collection_name="documents",
    connection=connection_string,
    use_jsonb=True,
)

remove_redundancy = EmbeddingsRedundantFilter(
    embeddings=embeddings, similarity_threshold=0.96
)


# Similiarity search
# str = search query(question), k = number of results to return
async def similarity_search(
    query: str, k: int = 5, score_threshold: float = 0.0
) -> list[dict]:
    results = vector_store.similarity_search_with_relevance_scores(query=query, k=k * 3)
    seen_content = set()
    unique_results = []

    for doc, score in results:
        if score < score_threshold:
            continue
            # Use first 200 chars as dedup key
        content_key = doc.page_content[:200]

        if content_key not in seen_content:
            seen_content.add(content_key)
            unique_results.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "source": doc.metadata.get("source", "unknown"),
                    "score": score,
                }
            )

            if len(unique_results) >= k:
                break

    return unique_results


def sanitize_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = "".join(
        char for char in text if char == "\n" or char == "\t" or ord(char) >= 32
    )
    return text.strip()


# Adding documents to vector stores after embeddings
async def add_documents(texts: list[str], metadatas: list[dict] = None):
    # Where embedding actually happens.
    cleaned_texts = [sanitize_text(text) for text in texts]

    # Filter out empty texts after cleaning
    valid_data = [
        (text, meta)
        for text, meta in zip(cleaned_texts, metadatas or [{}] * len(cleaned_texts))
        if text.strip()  # Only keep non-empty texts
    ]

    if not valid_data:
        print(". All texts were empty after cleaning")
        return

    valid_texts = [item[0] for item in valid_data]
    valid_metadatas = [item[1] for item in valid_data]

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, lambda: vector_store.add_texts(valid_texts, metadatas=valid_metadatas)
    )

    print(f" Added {len(valid_texts)} documents to vector store")

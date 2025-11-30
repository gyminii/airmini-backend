import asyncio

from app.lib.rag.ingestion import (
    ingest_pdf,
    ingest_url,
    ingest_text_file,
    ingest_documents_batch,
)
from app.lib.rag.vectorstore import similarity_search, vector_store


async def main():
    print("\n=== TEST 1: PDF INGEST ===")
    pdf = "data/documents/usa/Hazmat_booklet.pdf"
    try:
        pdf_res = await ingest_pdf(pdf)
        print(f"Loaded {len(pdf_res['texts'])} PDF chunks")
    except Exception as e:
        print(f"PDF ingest error: {e}")

    print("\n=== TEST 2: URL INGEST ===")
    url = "https://www.tsa.gov/travel/security-screening"
    try:
        url_res = await ingest_url(url)
        print(f"Loaded {len(url_res['texts'])} URL chunks")
    except Exception as e:
        print(f"URL ingest error: {e}")

    print("\n=== TEST 3: TEXT INGEST ===")
    txt = "data/documents/general/test.txt"
    try:
        txt_res = await ingest_text_file(txt)
        print(f"Loaded {len(txt_res['texts'])} text chunks")
    except Exception as e:
        print(f"Text ingest error: {e}")

    print("\n=== TEST 4: BATCH INGEST ===")
    try:
        await ingest_documents_batch(
            [
                {"type": "pdf", "path": pdf},
                {"type": "url", "url": url},
                {"type": "text", "path": txt},
            ]
        )
        print("Batch ingestion complete")
    except Exception as e:
        print(f"Batch ingest error: {e}")

    print("\n=== TEST 5: VECTORSTORE COUNT ===")
    try:
        # vector_store.client is the psycopg connection used internally
        with vector_store.connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM langchain_pg_embedding")
            count = cur.fetchone()[0]
            print(f"Total rows in langchain_pg_embedding: {count}")
    except Exception as e:
        print(f"Vectorstore count error: {e}")

    print("\n=== TEST 6: RETRIEVAL TEST ===")
    try:
        results = await similarity_search("TSA gun rules", k=3)
        print(f"Retrieved {len(results)} results:")
        for r in results:
            print(f"  - Score: {r['score']:.3f} | Source: {r['source']}")
    except Exception as e:
        print(f"Retrieval error: {e}")

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(main())

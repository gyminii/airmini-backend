from langchain_community.document_loaders import TextLoader

from .core import normalize_text, text_splitter


async def ingest_text_file(file_path: str, extra_metadata: dict | None = None) -> dict:
    """Ingest a text file into chunks"""
    loader = TextLoader(file_path)
    documents = loader.load()

    for doc in documents:
        doc.page_content = normalize_text(doc.page_content)

    chunks = text_splitter.split_documents(documents)

    texts = [chunk.page_content for chunk in chunks]
    base = {"source": file_path, "type": "text"}
    if extra_metadata:
        base.update(extra_metadata)
    metadatas = [dict(base) for _ in chunks]

    return {"texts": texts, "metadatas": metadatas}

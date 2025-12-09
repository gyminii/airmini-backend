from langchain_community.document_loaders import TextLoader

from app.lib.rag.config import redundancy_filter
from .core import normalize_text, text_splitter


async def ingest_text_file(file_path: str) -> dict:
    """Ingest a text file into chunks"""
    loader = TextLoader(file_path)
    documents = loader.load()

    for doc in documents:
        doc.page_content = normalize_text(doc.page_content)

    chunks = text_splitter.split_documents(documents)
    filtered_chunks = await redundancy_filter.atransform_documents(chunks)

    texts = [chunk.page_content for chunk in filtered_chunks]
    metadatas = [{"source": file_path, "type": "text"} for _ in filtered_chunks]

    return {"texts": texts, "metadatas": metadatas}

from app.lib.rag.config import redundancy_filter
from .core import normalize_text, text_splitter


async def ingest_pdf(file_path: str) -> dict:
    """Ingest a PDF file into chunks"""
    try:
        from langchain_community.document_loaders import UnstructuredPDFLoader
    except ImportError as e:
        raise RuntimeError(
            "UnstructuredPDFLoader requires the 'ingestion' "
            "(unstructured[docx,pdf]) to be installed. "
            "Run: uv sync --group ingestion"
        ) from e

    loader = UnstructuredPDFLoader(file_path, strategy="hi_res")
    documents = loader.load()

    for doc in documents:
        doc.page_content = normalize_text(doc.page_content)

    chunks = text_splitter.split_documents(documents)
    filtered_chunks = await redundancy_filter.atransform_documents(chunks)

    texts = [chunk.page_content for chunk in filtered_chunks]
    metadatas = [
        {
            "source": file_path,
            "type": "pdf",
            "page": chunk.metadata.get("page", 0),
        }
        for chunk in filtered_chunks
    ]

    return {"texts": texts, "metadatas": metadatas}

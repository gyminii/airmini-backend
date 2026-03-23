from .core import normalize_text, text_splitter


async def ingest_pdf(file_path: str, extra_metadata: dict | None = None) -> dict:
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

    texts = [chunk.page_content for chunk in chunks]
    base = {"source": file_path, "type": "pdf"}
    if extra_metadata:
        base.update(extra_metadata)
    metadatas = [
        {**base, "page": chunk.metadata.get("page", 0)}
        for chunk in chunks
    ]

    return {"texts": texts, "metadatas": metadatas}

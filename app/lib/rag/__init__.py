"""
RAG (Retrieval-Augmented Generation) module for travel knowledge base
"""

from app.lib.rag.vectorstore import similarity_search, add_documents
from app.lib.rag.retriever import (
    retrieve_web_results,
    retrieve_rag_results,
    retrieve_visa_requirements,
)
from app.lib.rag.formatters import (
    format_rag_sources,
    format_web_sources,
    format_visa_sources,
)

__all__ = [
    # Vector store
    "similarity_search",
    "add_documents",
    # Retrievers
    "retrieve_web_results",
    "retrieve_rag_results",
    "retrieve_visa_requirements",
    # Formatters
    "format_rag_sources",
    "format_web_sources",
    "format_visa_sources",
]

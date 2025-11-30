"""
RAG (Retrieval-Augmented Generation) module for travel knowledge base
"""
from app.lib.rag.vectorstore import similarity_search, add_documents

__all__ = ["similarity_search", "add_documents"]
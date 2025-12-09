from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_community.document_transformers import EmbeddingsRedundantFilter

from app.config import get_settings

settings = get_settings()

# Embeddings model
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=settings["openai_apikey"],
)

# Vector store
vector_store = PGVector(
    embeddings=embeddings,
    collection_name="documents",
    connection=settings["database_url"],
    use_jsonb=True,
)

# Redundancy filter for ingestion
redundancy_filter = EmbeddingsRedundantFilter(
    embeddings=embeddings,
    similarity_threshold=0.96,
)

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from pydantic import SecretStr

from app.config import get_settings

settings = get_settings()

# Embeddings model
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=SecretStr(settings["openai_apikey"]),
)

# Vector store
vector_store = PGVector(
    embeddings=embeddings,
    collection_name="documents",
    connection=settings["database_url"],
    use_jsonb=True,
)

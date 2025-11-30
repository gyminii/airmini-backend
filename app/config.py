from typing import TypedDict
from pydantic import SecretStr
from dotenv import load_dotenv
import os

# loading environment variables
load_dotenv()


class Settings(TypedDict):
    openai_apikey: SecretStr
    openai_model: str
    rapid_apikey: str
    tavily_apikey: str
    clerk_secretKey: str
    clerk_publishablekey: str
    jwt_key: str
    database_url: SecretStr
    vectordb_url: SecretStr


def get_settings() -> Settings:

    openai_apikey = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    rapid_apikey = os.getenv("RAPID_API_KEY")
    tavily_apikey = os.getenv("TAVILY_API_KEY")
    clerk_secretKey = os.getenv("CLERK_SECRET_KEY")
    clerk_publishablekey = os.getenv("CLERK_PUBLISHABLE_KEY")
    jwt_key = os.getenv("JWT_KEY")
    database_url = os.getenv("DATABASE_URL")
    vectordb_url = os.getenv("VECTOR_DATABASE_URL")

    if not openai_apikey:
        raise ValueError("No openai api key found in environment variables")
    if not rapid_apikey:
        raise ValueError("No rapid api key found in environment variables")
    if not tavily_apikey:
        raise ValueError("No rapid api key found in environment variables")
    if not clerk_secretKey:
        raise ValueError("No Clerk secret key found in environment variables")
    if not clerk_publishablekey:
        raise ValueError("No Clerk publishable key found in environment variables")
    if not jwt_key:
        raise ValueError("No Clerk JWT key found in environment variables")
    if not database_url:
        raise ValueError("No Datbase URL found in environment variables")
    if not vectordb_url:
        raise ValueError("No Vector Database URL found in environment variables")
    return {
        "openai_apikey": openai_apikey,
        "openai_model": openai_model,
        "rapid_apikey": rapid_apikey,
        "tavily_apikey": tavily_apikey,
        "clerk_secretKey": clerk_secretKey,
        "clerk_publishablekey": clerk_publishablekey,
        "jwt_key": jwt_key,
        "database_url": database_url,
        "vectordb_url": vectordb_url,
    }

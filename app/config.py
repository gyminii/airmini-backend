from typing import TypedDict, Optional
from dotenv import load_dotenv
import os

# loading environment variables
load_dotenv()


class Settings(TypedDict):
    openai_apikey: str
    openai_model: str
    rapid_apikey: str
    rapid_apihost: Optional[str]

    tavily_apikey: str
    clerk_secretKey: str
    clerk_publishablekey: str
    database_url: str


def get_settings() -> Settings:

    openai_apikey = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    rapid_apikey = os.getenv("RAPID_API_KEY")
    tavily_apikey = os.getenv("TAVILY_API_KEY")
    clerk_secretKey = os.getenv("CLERK_SECRET_KEY")
    clerk_publishablekey = os.getenv("CLERK_PUBLISHABLE_KEY")
    database_url = os.getenv("DATABASE_URL")
    rapid_apihost = os.getenv("RAPIDAPI_HOST")

    if not openai_apikey:
        raise ValueError("No openai api key found in environment variables")
    if not rapid_apikey:
        raise ValueError("No rapid api key found in environment variables")
    if not tavily_apikey:
        raise ValueError("No Tavily api key found in environment variables")
    if not clerk_secretKey:
        raise ValueError("No Clerk secret key found in environment variables")
    if not clerk_publishablekey:
        raise ValueError("No Clerk publishable key found in environment variables")
    if not database_url:
        raise ValueError("No Database URL found in environment variables")
    # Normalize to plain postgresql:// so each consumer can add its own driver
    for prefix in ("postgresql+psycopg2://", "postgresql+asyncpg://"):
        if database_url.startswith(prefix):
            database_url = "postgresql://" + database_url[len(prefix):]
            break
    # Strip all libpq query params (sslmode, channel_binding, etc.)
    # Each consumer adds its own driver and SSL config
    from urllib.parse import urlparse, urlunparse
    database_url = urlunparse(urlparse(database_url)._replace(query=""))
    return {
        "openai_apikey": openai_apikey,
        "openai_model": openai_model,
        "rapid_apikey": rapid_apikey,
        "tavily_apikey": tavily_apikey,
        "clerk_secretKey": clerk_secretKey,
        "clerk_publishablekey": clerk_publishablekey,
        "database_url": database_url,
        "rapid_apihost": rapid_apihost,
    }

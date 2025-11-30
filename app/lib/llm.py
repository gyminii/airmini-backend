from langchain_openai import ChatOpenAI
from app.config import get_settings

settings = get_settings()

# Openai chat definition
chat_model = ChatOpenAI(
    api_key=settings["openai_apikey"],
    temperature=0.8,
    model=settings["openai_model"],
)

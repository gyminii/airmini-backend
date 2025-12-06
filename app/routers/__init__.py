from fastapi import APIRouter
from app.routers import chat, chats

api_router = APIRouter()


# Sub routes
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])

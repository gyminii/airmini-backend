from fastapi import APIRouter
from app.routers import chat, chats

# Create main router
api_router = APIRouter()


# Sub routes
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])
# Add more routers here as you build them

from fastapi import APIRouter
from app.routers import chat

# Create main router
api_router = APIRouter()

# Sub routes
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# Add more routers here as you build them

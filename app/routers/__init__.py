from fastapi import APIRouter
from app.routers import chat, chats, trip_context, admin

api_router = APIRouter()


# Sub routes
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])
api_router.include_router(
    trip_context.router, prefix="/trip-context", tags=["trip-context"]
)
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

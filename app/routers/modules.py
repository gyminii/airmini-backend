import logging
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models import Chat as ChatORM

#
logger = logging.getLogger(__name__)


def is_user_authenticated(current_user: dict | None) -> str:
    """Verify user is authenticated and return user_id"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_user["user_id"]


async def is_chat_valid(
    chat_id: str,
    user_id: str,
    db: AsyncSession,
) -> ChatORM:
    """
    Validate chat_id format, existence, and ownership.
    Returns the Chat object if valid.
    Raises HTTPException if invalid.
    """
    # Validate UUID format
    try:
        chat_uuid = uuid.UUID(chat_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat_id",
        )

    # Check existence and ownership
    result = await db.execute(
        select(ChatORM).where(ChatORM.id == chat_uuid, ChatORM.user_id == user_id)
    )

    chat = result.scalar_one_or_none()
    if chat == None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access denied",
        )
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    return chat

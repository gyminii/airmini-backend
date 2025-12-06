import logging
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.db import get_db
from app.database.models import Chat as ChatORM, Message as MessageORM, MessageRole
from app.auth.clerk import get_authenticated_user
from app.lib.graph import generate_chat_title
from app.routers.modules import is_chat_valid, is_user_authenticated
from app.schemas.chat import (
    ChatSummary,
    ChatUpdate,
    MessageRead,
    ClaimConversationRequest,
    ClaimMessageInput,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=List[ChatSummary])
async def list_chats(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_authenticated_user),
):
    """List all chats for the authenticated user"""
    user_id = is_user_authenticated(current_user)

    result = await db.execute(
        select(ChatORM)
        .where(ChatORM.user_id == user_id)
        .order_by(ChatORM.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{chat_id}/messages", response_model=List[MessageRead])
async def get_chat_messages(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_authenticated_user),
):
    """Get all messages for a specific chat"""
    user_id = is_user_authenticated(current_user)

    # Validate chat ownership
    chat = await is_chat_valid(chat_id, user_id, db)

    result = await db.execute(
        select(MessageORM)
        .where(MessageORM.chat_id == chat.id)
        .order_by(MessageORM.created_at.asc())
    )
    return result.scalars().all()


@router.get("/{chat_id}", response_model=ChatSummary)
async def get_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_authenticated_user),
):
    """Get a specific chat by ID"""
    user_id = is_user_authenticated(current_user)
    logger.debug(f"Fetching chat {chat_id} for user {user_id}")

    chat = await is_chat_valid(chat_id, user_id, db)
    return chat


@router.patch("/{chat_id}", response_model=ChatSummary)
async def update_chat(
    chat_id: str,
    payload: ChatUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_authenticated_user),
):
    """Update chat properties (e.g., title)"""
    user_id = is_user_authenticated(current_user)
    chat = await is_chat_valid(chat_id, user_id, db)

    if payload.title is not None:
        chat.title = payload.title

    await db.commit()
    await db.refresh(chat)
    return chat


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_authenticated_user),
):
    """Delete a chat and all related messages/trip context (CASCADE)"""
    user_id = is_user_authenticated(current_user)
    chat = await is_chat_valid(chat_id, user_id, db)

    # Database CASCADE will automatically delete related messages and trip_context
    await db.delete(chat)
    await db.commit()


#
@router.post("/claim-conversation", response_model=ChatSummary)
async def claim_conversation(
    request: ClaimConversationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_authenticated_user),
):
    """Save an anonymous conversation to the authenticated user's account"""
    user_id = is_user_authenticated(current_user)

    # Generate title from first message if not provided
    title = request.title
    if not title and request.messages:
        first_user_msg = next(
            (m.content for m in request.messages if m.role == "user"), None
        )
        if first_user_msg:
            title = await generate_chat_title(first_user_msg)

    # Create chat
    chat = ChatORM(user_id=user_id, title=title or "New Chat")
    db.add(chat)
    await db.flush()

    # Add all messages
    for msg in request.messages:
        message = MessageORM(
            chat_id=chat.id,
            role=MessageRole[msg.role.upper()],
            content=msg.content,
        )
        db.add(message)

    await db.commit()
    await db.refresh(chat)

    return chat

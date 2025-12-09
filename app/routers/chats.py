import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_core.messages import HumanMessage

from app.database.db import get_db
from app.database.models import Chat as ChatORM
from app.auth.clerk import get_authenticated_user
from app.lib.provider import get_graph
from app.routers.modules import is_chat_valid, is_user_authenticated
from app.schemas.chat import ChatSummary, ChatUpdate

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


@router.get("/{chat_id}/messages")
async def get_chat_messages(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_authenticated_user),
):
    """Get messages from checkpointer"""
    user_id = is_user_authenticated(current_user)
    await is_chat_valid(chat_id, user_id, db)

    graph = get_graph()
    config = {"configurable": {"thread_id": chat_id}}
    state = await graph.aget_state(config)

    if not state or not state.values.get("messages"):
        return []

    return [
        {
            "role": "user" if isinstance(msg, HumanMessage) else "assistant",
            "content": msg.content,
        }
        for msg in state.values["messages"]
    ]


@router.get("/{chat_id}", response_model=ChatSummary)
async def get_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_authenticated_user),
):
    """Get a specific chat by ID"""
    user_id = is_user_authenticated(current_user)
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

    await db.delete(chat)
    await db.commit()

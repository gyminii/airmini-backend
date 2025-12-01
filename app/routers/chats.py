from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database.db import get_db
from app.database.models import (
    Chat as ChatORM,
    Message as MessageORM,
    TripContext as TripContextORM,
)
from app.auth.clerk import get_current_user
from app.routers.modules import is_chat_valid, is_user_authenticated
from app.schemas.chat import ChatSummary, ChatUpdate

router = APIRouter()


@router.get("", response_model=List[ChatSummary])
async def list_chats(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):
    user_id = is_user_authenticated(current_user)

    result = await db.execute(
        select(ChatORM)
        .where(ChatORM.user_id == user_id)
        .order_by(ChatORM.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{chat_id}", response_model=ChatSummary)
async def get_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):
    user_id = is_user_authenticated(current_user)
    _, chat = await is_chat_valid(chat_id, user_id, db)
    return chat


@router.patch("/{chat_id}", response_model=ChatSummary)
async def update_chat(
    chat_id: str,
    payload: ChatUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):
    user_id = is_user_authenticated(current_user)

    _, chat = await is_chat_valid(chat_id, user_id, db)

    if payload.title is not None:
        chat.title = payload.title

    await db.commit()
    await db.refresh(chat)
    return chat


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):
    user_id = is_user_authenticated(current_user)
    chat_uuid, _ = await is_chat_valid(chat_id, user_id, db)

    await db.execute(delete(MessageORM).where(MessageORM.chat_id == chat_uuid))
    await db.execute(delete(TripContextORM).where(TripContextORM.chat_id == chat_uuid))
    await db.execute(delete(ChatORM).where(ChatORM.id == chat_uuid))

    await db.commit()
    return


@router.post("/{chat_id}/claim", status_code=status.HTTP_204_NO_CONTENT)
async def claim_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):
    user_id = is_user_authenticated(current_user)

    try:
        chat_uuid = UUID(chat_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat_id",
        )

    result = await db.execute(select(ChatORM).where(ChatORM.id == chat_uuid))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    if not str(chat.user_id).startswith("anon_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat is already associated with an account",
        )

    chat.user_id = user_id
    await db.commit()
    return

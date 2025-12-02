from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.db import get_db
from app.database.models import Message as MessageORM
from app.auth.clerk import get_authenticated_user
from app.schemas.chat import MessageRead
from app.routers.modules import is_user_authenticated, is_chat_valid

router = APIRouter()


@router.get("/{chat_id}/messages", response_model=List[MessageRead])
async def list_messages(
    chat_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_authenticated_user),
):
    user_id = is_user_authenticated(current_user)
    chat_uuid, _ = await is_chat_valid(chat_id, user_id, db)

    messages_result = await db.execute(
        select(MessageORM)
        .where(MessageORM.chat_id == chat_uuid)
        .order_by(MessageORM.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return messages_result.scalars().all()

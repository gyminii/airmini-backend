from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_db
from app.database.models import (
    Chat as ChatORM,
    Language,
    Message as MessageORM,
    TripContext as TripContextORM,
    MessageRole,
)

from app.lib.graph import generate_chat_title
from app.schemas.chat import ChatRequest, ChatResponse, ChatSummary, TripContext
from app.auth.clerk import get_authenticated_user, get_optional_user
from app.lib.provider import get_graph
from langchain_core.messages import HumanMessage, AIMessage
from typing import AsyncGenerator, Optional
import uuid
import json

router = APIRouter()


# user or anonymous user
def resolve_user_id(current_user: Optional[dict]) -> str:
    if current_user:
        return current_user["user_id"]
    return f"anon_{uuid.uuid4()}"


async def get_or_create_chat(
    db: AsyncSession,
    user_id: str,
    chat_id: Optional[str],
    first_message: Optional[str] = None,
) -> ChatORM:
    if chat_id:
        try:
            chat_uuid = uuid.UUID(chat_id)
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
        return chat

    title = None
    if first_message:
        title = await generate_chat_title(first_message)

    chat = ChatORM(user_id=user_id, title=title or "New Chat")
    db.add(chat)
    await db.flush()
    return chat


async def upsert_trip_context(
    db: AsyncSession,
    chat_id,
    trip_context_request: Optional[TripContextORM],
) -> Optional[dict]:
    if not trip_context_request:
        result = await db.execute(
            select(TripContextORM).where(TripContextORM.chat_id == chat_id)
        )
        trip_context_orm = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(TripContextORM).where(TripContextORM.chat_id == chat_id)
        )
        trip_context_orm = result.scalar_one_or_none()
        if trip_context_orm:
            trip_context_orm.ui_language = Language[trip_context_request.ui_language]
            trip_context_orm.answer_language = Language[
                trip_context_request.answer_language
            ]
            trip_context_orm.nationality_country_code = (
                trip_context_request.nationality_country_code
            )
            trip_context_orm.origin_country_code = (
                trip_context_request.origin_country_code
            )
            trip_context_orm.origin_city_or_airport = (
                trip_context_request.origin_city_or_airport
            )
            trip_context_orm.destination_country_code = (
                trip_context_request.destination_country_code
            )
            trip_context_orm.destination_city_or_airport = (
                trip_context_request.destination_city_or_airport
            )
            trip_context_orm.trip_type = trip_context_request.trip_type
            trip_context_orm.departure_date = trip_context_request.departure_date
            trip_context_orm.return_date = trip_context_request.return_date
            trip_context_orm.airline_code = trip_context_request.airline_code
            trip_context_orm.cabin = trip_context_request.cabin
            trip_context_orm.purpose = trip_context_request.purpose
        else:
            trip_context_orm = TripContextORM(
                chat_id=chat_id,
                ui_language=Language[trip_context_request.ui_language],
                answer_language=Language[trip_context_request.answer_language],
                nationality_country_code=trip_context_request.nationality_country_code,
                origin_country_code=trip_context_request.origin_country_code,
                origin_city_or_airport=trip_context_request.origin_city_or_airport,
                destination_country_code=trip_context_request.destination_country_code,
                destination_city_or_airport=trip_context_request.destination_city_or_airport,
                trip_type=trip_context_request.trip_type,
                departure_date=trip_context_request.departure_date,
                return_date=trip_context_request.return_date,
                airline_code=trip_context_request.airline_code,
                cabin=trip_context_request.cabin,
                purpose=trip_context_request.purpose,
            )
            db.add(trip_context_orm)

        await db.flush()

    if not trip_context_orm:
        return None

    def get_lang_value(lang_field):
        if lang_field is None:
            return "EN"
        return lang_field.value if hasattr(lang_field, "value") else lang_field

    return {
        "ui_language": get_lang_value(trip_context_orm.ui_language),
        "answer_language": get_lang_value(trip_context_orm.answer_language),
        "nationality_country_code": trip_context_orm.nationality_country_code,
        "origin_country_code": trip_context_orm.origin_country_code,
        "origin_city_or_airport": trip_context_orm.origin_city_or_airport,
        "destination_country_code": trip_context_orm.destination_country_code,
        "destination_city_or_airport": trip_context_orm.destination_city_or_airport,
        "trip_type": trip_context_orm.trip_type,
        "departure_date": trip_context_orm.departure_date,
        "return_date": trip_context_orm.return_date,
        "airline_code": trip_context_orm.airline_code,
        "cabin": trip_context_orm.cabin,
        "purpose": trip_context_orm.purpose,
    }


async def save_user_message_and_get_history(
    db: AsyncSession,
    chat_id,
    user_content: str,
    limit: int = 20,
):
    user_message = MessageORM(
        chat_id=chat_id,
        role=MessageRole.USER,
        content=user_content,
    )
    db.add(user_message)
    await db.flush()

    messages_result = await db.execute(
        select(MessageORM)
        .where(MessageORM.chat_id == chat_id)
        .order_by(MessageORM.created_at.asc())
        .limit(limit)
    )
    return messages_result.scalars().all()


async def save_assistant_message(
    db: AsyncSession,
    chat_id,
    content: str,
):
    ai_message = MessageORM(
        chat_id=chat_id,
        role=MessageRole.ASSISTANT,
        content=content,
    )
    db.add(ai_message)
    await db.commit()


def build_langchain_messages(message_history, latest_user_message: str):
    lc_messages = []
    for msg in message_history[:-1]:
        if msg.role == MessageRole.USER:
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            lc_messages.append(AIMessage(content=msg.content))

    lc_messages.append(HumanMessage(content=latest_user_message))
    return lc_messages


def build_initial_graph_state(lc_messages, trip_context_dict: Optional[dict]):
    return {
        "messages": lc_messages,
        "trip_context": trip_context_dict,
        "query": None,
        "query_type": None,
        "needs_visa_api": False,
        "needs_web_search": False,
        "needs_rag": False,
        "rag_results": None,
        "web_results": None,
        "visa_results": None,
        "sources_used": [],
        "relevance_passed": False,
        "retry_count": 0,
    }


def sse_event(data: dict) -> str:
    """Format data as SSE event"""
    return f"data: {json.dumps(data)}\n\n"


# Authenticated streaming
async def graph_token_stream(
    graph,
    graph_state: dict,
    chat_id,
    chat_title: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Stream in AI SDK Data Stream Protocol (SSE format)"""
    full_text = ""
    message_id = f"msg_{chat_id}"
    text_id = f"text_{chat_id}"

    yield sse_event({"type": "start", "messageId": message_id})

    yield sse_event(
        {
            "type": "data-metadata",
            "data": {"chatId": str(chat_id), "title": chat_title},
            "transient": True,
        }
    )

    yield sse_event({"type": "text-start", "id": text_id})

    async for chunk in graph.astream(
        graph_state,
        config={"configurable": {"thread_id": str(chat_id)}},
        stream_mode=["custom"],
    ):
        kind, data = chunk
        if kind != "custom":
            continue

        if isinstance(data, str):
            full_text += data
            yield sse_event({"type": "text-delta", "id": text_id, "delta": data})

    # Send text block end
    yield sse_event({"type": "text-end", "id": text_id})

    # Send message finish
    yield sse_event({"type": "finish"})

    # Send done marker
    yield "data: [DONE]\n\n"

    await save_assistant_message(db, chat_id, full_text)


# Unauthenticated streaming
async def graph_token_stream_anon(
    message: str,
    trip_context: Optional[dict] = None,
) -> AsyncGenerator[str, None]:
    """Stream for anonymous users - no DB persistence"""
    message_id = f"msg_{uuid.uuid4()}"
    text_id = f"text_{uuid.uuid4()}"

    yield sse_event({"type": "start", "messageId": message_id})
    yield sse_event({"type": "text-start", "id": text_id})

    lc_messages = [HumanMessage(content=message)]

    graph_state = build_initial_graph_state(lc_messages, trip_context)
    graph = get_graph()

    async for chunk in graph.astream(
        graph_state,
        config={"configurable": {"thread_id": message_id}},
        stream_mode=["custom"],
    ):
        kind, data = chunk
        if kind != "custom":
            continue

        if isinstance(data, str):
            yield sse_event({"type": "text-delta", "id": text_id, "delta": data})

    yield sse_event({"type": "text-end", "id": text_id})
    yield sse_event({"type": "finish"})
    yield "data: [DONE]\n\n"


@router.post("/stream")
async def create_chat_message_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    user_id = resolve_user_id(current_user)
    is_anonymous = user_id.startswith("anon_")

    if is_anonymous:
        return StreamingResponse(
            graph_token_stream_anon(
                message=request.message,
                trip_context=request.trip_context,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "x-vercel-ai-ui-message-stream": "v1",
            },
        )
    chat = await get_or_create_chat(
        db,
        user_id=user_id,
        chat_id=request.chat_id,
        first_message=(request.message if not request.chat_id else None),
    )

    trip_context_dict = await upsert_trip_context(
        db,
        chat_id=chat.id,
        trip_context_request=request.trip_context,
    )

    message_history = await save_user_message_and_get_history(
        db,
        chat_id=chat.id,
        user_content=request.message,
        limit=20,
    )

    lc_messages = build_langchain_messages(
        message_history, latest_user_message=request.message
    )

    graph_state = build_initial_graph_state(lc_messages, trip_context_dict)
    graph = get_graph()

    return StreamingResponse(
        graph_token_stream(
            graph=graph,
            graph_state=graph_state,
            chat_id=chat.id,
            chat_title=chat.title,
            db=db,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Chat-Id": str(chat.id),
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )

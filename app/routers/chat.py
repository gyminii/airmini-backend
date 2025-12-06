from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_core.messages import HumanMessage
from typing import AsyncGenerator, Optional
import uuid
import json

from app.database.db import get_db
from app.database.models import Chat as ChatORM, Language, TripContext as TripContextORM
from app.lib.graph import generate_chat_title
from app.schemas.chat import ChatRequest, TripContext
from app.auth.clerk import get_optional_user
from app.lib.provider import get_graph

router = APIRouter()


def resolve_user_id(current_user: Optional[dict]) -> str:
    """Get user ID or generate anonymous ID"""
    if current_user:
        return current_user["user_id"]
    return f"anon_{uuid.uuid4()}"


async def get_or_create_chat(
    db: AsyncSession,
    user_id: str,
    chat_id: Optional[str],
    first_message: Optional[str] = None,
) -> ChatORM:
    """Get existing chat or create new one"""
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

    title = await generate_chat_title(first_message) if first_message else None
    chat = ChatORM(user_id=user_id, title=title or "New Chat")
    db.add(chat)
    await db.flush()
    return chat


async def upsert_trip_context(
    db: AsyncSession,
    chat_id,
    trip_context_request: Optional[TripContext],
) -> Optional[dict]:
    """Create or update trip context for a chat"""
    result = await db.execute(
        select(TripContextORM).where(TripContextORM.chat_id == chat_id)
    )
    trip_context_orm = result.scalar_one_or_none()

    if trip_context_request:
        if trip_context_orm:
            # Update existing
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
            # Create new
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


def build_initial_graph_state(
    lc_messages: list, trip_context_dict: Optional[dict]
) -> dict:
    """Build initial state for graph execution"""
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


async def graph_token_stream(
    graph,
    graph_state: dict,
    chat_id,
    chat_title: str,
) -> AsyncGenerator[str, None]:
    """Stream for authenticated users"""
    message_id = f"msg_{chat_id}"
    text_id = f"text_{chat_id}"
    text_started = False

    yield sse_event({"type": "start", "messageId": message_id})
    yield sse_event(
        {
            "type": "data-metadata",
            "data": {"chatId": str(chat_id), "title": chat_title},
            "transient": True,
        }
    )

    async for chunk in graph.astream(
        graph_state,
        config={"configurable": {"thread_id": str(chat_id)}},
        stream_mode=["custom"],
    ):
        kind, data = chunk
        if kind != "custom":
            continue

        # Handle thought events - use data-thought type
        if isinstance(data, dict) and data.get("type") == "thought":
            yield sse_event(
                {
                    "type": "data-thought",
                    "data": {
                        "content": data.get("content", ""),
                        "status": "pending",
                    },
                }
            )
        # Handle text streaming
        elif isinstance(data, str):
            if not text_started:
                yield sse_event({"type": "text-start", "id": text_id})
                text_started = True
            yield sse_event({"type": "text-delta", "id": text_id, "delta": data})

    if text_started:
        yield sse_event({"type": "text-end", "id": text_id})

    yield sse_event({"type": "finish"})
    yield "data: [DONE]\n\n"


async def graph_token_stream_anon(
    message: str,
    trip_context: Optional[dict] = None,
) -> AsyncGenerator[str, None]:
    """Stream for anonymous users - no DB persistence"""
    message_id = f"msg_{uuid.uuid4()}"
    text_id = f"text_{uuid.uuid4()}"
    text_started = False

    yield sse_event({"type": "start", "messageId": message_id})

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

        if isinstance(data, dict) and data.get("type") == "thought":
            yield sse_event(
                {
                    "type": "data-thought",
                    "data": {
                        "content": data.get("content", ""),
                        "status": "pending",
                    },
                }
            )
        elif isinstance(data, str):
            if not text_started:
                yield sse_event({"type": "text-start", "id": text_id})
                text_started = True
            yield sse_event({"type": "text-delta", "id": text_id, "delta": data})

    if text_started:
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

    print(f"=== Incoming request ===")
    print(f"chat_id from request: {request.chat_id}")
    print(f"message: {request.message[:50]}...")

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
        first_message=request.message if not request.chat_id else None,
    )

    trip_context_dict = await upsert_trip_context(
        db,
        chat_id=chat.id,
        trip_context_request=request.trip_context,
    )

    graph = get_graph()

    # Load existing messages from checkpointer
    config = {"configurable": {"thread_id": str(chat.id)}}
    state = await graph.aget_state(config)

    # DEBUG: Log what we got from checkpointer
    print(f"=== Loading chat {chat.id} ===")
    print(f"State exists: {state is not None}")
    if state:
        print(f"State.values type: {type(state.values)}")
        print(f"State.values keys: {state.values.keys() if state.values else 'None'}")
        print(f"State.values: {state.values}")
    if state and state.values:
        existing_messages = state.values.get("messages", [])
        print(f"Existing messages count: {len(existing_messages)}")
        for i, msg in enumerate(existing_messages):
            print(f"  [{i}] {msg.__class__.__name__}: {msg.content[:50]}...")
    else:
        print("No existing state/messages found")

    if state and state.values.get("messages"):
        lc_messages = list(state.values["messages"])
        lc_messages.append(HumanMessage(content=request.message))
    else:
        lc_messages = [HumanMessage(content=request.message)]

    print(f"Total messages being sent to graph: {len(lc_messages)}")

    graph_state = build_initial_graph_state(lc_messages, trip_context_dict)

    return StreamingResponse(
        graph_token_stream(
            graph=graph,
            graph_state=graph_state,
            chat_id=chat.id,
            chat_title=chat.title,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Chat-Id": str(chat.id),
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )

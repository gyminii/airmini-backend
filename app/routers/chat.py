from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_db
from app.database.models import (
    Chat as ChatORM,
    Message as MessageORM,
    TripContext as TripContextORM,
    MessageRole,
)
from app.schemas.chat import ChatRequest, ChatResponse, TripContext
from app.auth.clerk import get_current_user
from app.lib.provider import get_graph
from langchain_core.messages import HumanMessage, AIMessage
from typing import Optional
import uuid

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def create_chat_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):
    # Step 1: Determine user_id
    if current_user:
        user_id = current_user["user_id"]
    else:
        user_id = f"anon_{uuid.uuid4()}"

    print(f"User: {user_id}")

    # getting | creating session
    # idk if this is ideal but i thought it would be
    # more efficient doing conditional id assignment
    # as functionally it does the same thing
    if request.session_id:
        try:
            chat_uuid = uuid.UUID(request.session_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session_id",
            )

        result = await db.execute(select(ChatORM).where(ChatORM.id == chat_uuid))
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found",
            )
    else:
        chat = ChatORM(user_id=user_id)
        db.add(chat)
        await db.flush()

    print(f"Chat ID: {chat.id}")

    # check/ updating trip context
    trip_context_result = await db.execute(
        select(TripContextORM).where(TripContextORM.chat_id == chat.id)
    )
    trip_context_orm = trip_context_result.scalar_one_or_none()

    if request.trip_context:
        if trip_context_orm:
            # Update existing
            trip_context_orm.ui_language = request.trip_context.ui_language
            trip_context_orm.answer_language = request.trip_context.answer_language
            trip_context_orm.nationality_country_code = (
                request.trip_context.nationality_country_code
            )
            trip_context_orm.origin_country_code = (
                request.trip_context.origin_country_code
            )
            trip_context_orm.origin_city_or_airport = (
                request.trip_context.origin_city_or_airport
            )
            trip_context_orm.destination_country_code = (
                request.trip_context.destination_country_code
            )
            trip_context_orm.destination_city_or_airport = (
                request.trip_context.destination_city_or_airport
            )
            trip_context_orm.trip_type = request.trip_context.trip_type
            trip_context_orm.departure_date = request.trip_context.departure_date
            trip_context_orm.return_date = request.trip_context.return_date
            trip_context_orm.airline_code = request.trip_context.airline_code
            trip_context_orm.cabin = request.trip_context.cabin
            trip_context_orm.purpose = request.trip_context.purpose
        else:
            # Create new
            trip_context_orm = TripContextORM(
                chat_id=chat.id,
                ui_language=request.trip_context.ui_language,
                answer_language=request.trip_context.answer_language,
                nationality_country_code=request.trip_context.nationality_country_code,
                origin_country_code=request.trip_context.origin_country_code,
                origin_city_or_airport=request.trip_context.origin_city_or_airport,
                destination_country_code=request.trip_context.destination_country_code,
                destination_city_or_airport=request.trip_context.destination_city_or_airport,
                trip_type=request.trip_context.trip_type,
                departure_date=request.trip_context.departure_date,
                return_date=request.trip_context.return_date,
                airline_code=request.trip_context.airline_code,
                cabin=request.trip_context.cabin,
                purpose=request.trip_context.purpose,
            )
            db.add(trip_context_orm)
        await db.flush()

    needs_onboarding = trip_context_orm is None

    # ORM -> Dict
    trip_context_dict = None
    if trip_context_orm:
        trip_context_dict = {
            "ui_language": (
                trip_context_orm.ui_language if trip_context_orm.ui_language else None
            ),
            "answer_language": (
                trip_context_orm.answer_language
                if trip_context_orm.answer_language
                else None
            ),
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

    # saving user msg
    user_message = MessageORM(
        chat_id=chat.id, role=MessageRole.USER, content=request.message
    )
    db.add(user_message)
    await db.flush()

    # loading chat history limiting to 20
    messages_result = await db.execute(
        select(MessageORM)
        .where(MessageORM.chat_id == chat.id)
        .order_by(MessageORM.created_at.asc())
        .limit(20)
    )
    message_history = messages_result.scalars().all()

    # storing in langchian message
    lc_messages = []
    for msg in message_history[:-1]:  # Exclude current message
        if msg.role == MessageRole.USER:
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            lc_messages.append(AIMessage(content=msg.content))

    # adding user's msg
    lc_messages.append(HumanMessage(content=request.message))

    print(f"Running agent with {len(lc_messages)} messages...")

    graph_state = {
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

    graph = get_graph()

    result = await graph.ainvoke(
        graph_state, config={"configurable": {"thread_id": str(chat.id)}}
    )

    # retrieving ai msg
    ai_response = result["messages"][-1].content
    print(f"Agent response: {ai_response[:100]}...")

    # saving ai msg
    ai_message = MessageORM(
        chat_id=chat.id, role=MessageRole.ASSISTANT, content=ai_response
    )
    db.add(ai_message)

    # commit the changes
    await db.commit()
    print("Committed to DB")

    return ChatResponse(
        message=ai_response,
        session_id=str(chat.id),
        trip_context=(
            TripContext(**trip_context_dict) if trip_context_dict else TripContext()
        ),
        needs_onboarding=needs_onboarding,
        source_info={
            "sources": result.get("sources_used", []),
            "query_type": result.get("query_type"),
        },
    )

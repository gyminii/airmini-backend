from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from sympy import det

from app.auth.clerk import get_current_user
from app.database.db import get_db
from app.database.models import (
    Chat as ChatORM,
    Message as MessageORM,
    TripContext as TripContextORM,
    MessageRole,
    Language,
)
from app.schemas.chat import ChatRequest, ChatResponse, TripContext as TripContextSchema

from app.lib.graph import test_graph
from langchain_core.messages import HumanMessage

app = FastAPI()

# https://rudaks.tistory.com/entry/langgraph-%EA%B7%B8%EB%9E%98%ED%94%84%EB%A5%BC-%EB%B9%84%EB%8F%99%EA%B8%B0%EB%A1%9C-%EC%8B%A4%ED%96%89%ED%95%98%EB%8A%94-%EB%B0%A9%EB%B2%95
# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def hello():
    return "hello bro"


def update_trip_context_orm(schema, orm):
    data = schema.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key in ("ui_language", "answer_language") and value is not None:
            value = Language(value)
        setattr(orm, key, value)


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):

    if current_user:
        user_id = current_user["user_id"]
    else:
        user_id = f"anon_{uuid.uuid4()}"
    print(f"📝 User: {user_id}")

    if request.session_id:
        result = await db.execute(
            select(ChatORM).where(ChatORM.id == uuid.UUID(request.session_id))
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )
    else:
        chat = ChatORM(user_id=user_id)
        db.add(chat)
        await db.flush()
    print(f"Chat ID: {chat.id}")

    user_message = MessageORM(
        chat_id=chat.id, role=MessageRole.USER, content=request.message
    )
    db.add(user_message)
    print(f"🤖 Running LangGraph agent...")
    graph_state = {
        "messages": [HumanMessage(content=request.message)],
        "trip_context": None,  # We'll add this logic later
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

    result = await test_graph.ainvoke(
        graph_state, config={"configurable": {"thread_id": str(chat.id)}}
    )
    ai_response = result["messages"][-1].content
    print(f"🤖 Agent response: {ai_response[:100]}...")

    ai_message = MessageORM(
        chat_id=chat.id, role=MessageRole.ASSISTANT, content=ai_response
    )
    db.add(ai_message)

    await db.commit()

    print(f"✅ Committed to DB")

    return ChatResponse(
        message=ai_response,
        session_id=str(chat.id),
        trip_context=TripContextSchema(),
        needs_onboarding=True,
        source_info={
            "sources": result.get("sources_used", []),
            "query_type": result.get("query_type"),
        },
    )

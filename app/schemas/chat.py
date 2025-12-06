from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict
from datetime import datetime
from uuid import UUID, uuid4


# fast api dicts
class TripContext(BaseModel):
    ui_language: Literal["EN", "KO"] = "EN"
    answer_language: Literal["EN", "KO"] = "EN"

    nationality_country_code: Optional[str] = None

    origin_country_code: Optional[str] = None
    origin_city_or_airport: Optional[str] = None

    destination_country_code: Optional[str] = None
    destination_city_or_airport: Optional[str] = None

    trip_type: Optional[Literal["one_way", "round_trip"]] = None
    departure_date: Optional[str] = None
    return_date: Optional[str] = None

    airline_code: Optional[str] = None
    cabin: Optional[Literal["economy", "premium", "business", "first"]] = None
    purpose: Optional[Literal["tourism", "business", "family", "study", "other"]] = None


class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    trip_context: Optional[TripContext] = None
    stream: bool = False


class ChatResponse(BaseModel):
    message: str
    chat_id: Optional[str] = None
    trip_context: TripContext
    needs_onboarding: bool
    source_info: Optional[Dict] = None


class ChatSummary(BaseModel):
    id: UUID
    title: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes: True


class MessageRead(BaseModel):
    id: UUID
    chat_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatUpdate(BaseModel):
    title: Optional[str] = None


class ClaimMessageInput(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ClaimConversationRequest(BaseModel):
    messages: List[ClaimMessageInput]

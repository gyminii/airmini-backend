from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict
from datetime import datetime
import uuid


class TripContext(BaseModel):
    ui_language: Literal["en", "ko"] = "en"
    answer_language: Literal["en", "ko"] = "en"

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


class ChatSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    trip_context: Optional[TripContext] = None
    message_history: List[Dict] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    # user_id: str
    session_id: Optional[str] = None
    trip_context: Optional[TripContext] = None


class ChatResponse(BaseModel):
    message: str
    session_id: str
    trip_context: TripContext
    needs_onboarding: bool
    source_info: Optional[Dict] = None

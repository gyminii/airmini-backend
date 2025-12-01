# app/database/models.py
import enum
import uuid
from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.base import Base


class MessageRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Language(enum.Enum):
    EN = "EN"
    KO = "KO"


def utcnow():
    return datetime.now(timezone.utc)


class Chat(Base):
    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    messages = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan"
    )
    trip_context = relationship(
        "TripContext",
        back_populates="chat",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(
        UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    chat = relationship("Chat", back_populates="messages")


class TripContext(Base):
    __tablename__ = "trip_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
    )

    ui_language = Column(Enum(Language), default=Language.EN)
    answer_language = Column(Enum(Language), default=Language.EN)

    nationality_country_code = Column(String, nullable=True)
    origin_country_code = Column(String, nullable=True)
    origin_city_or_airport = Column(String, nullable=True)
    destination_country_code = Column(String, nullable=True)
    destination_city_or_airport = Column(String, nullable=True)
    trip_type = Column(String, nullable=True)
    departure_date = Column(String, nullable=True)
    return_date = Column(String, nullable=True)
    airline_code = Column(String, nullable=True)
    cabin = Column(String, nullable=True)
    purpose = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    chat = relationship("Chat", back_populates="trip_context")

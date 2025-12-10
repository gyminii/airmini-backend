from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database.db import get_db
from app.database.models import TripContext as TripContextORM, Language
from app.schemas.chat import TripContext
from app.auth.clerk import get_authenticated_user

router = APIRouter()


def serialize_trip_context(tc: TripContextORM) -> dict:
    def get_lang(lang_field):
        if lang_field is None:
            return "EN"
        return lang_field.value if hasattr(lang_field, "value") else lang_field

    return {
        "ui_language": get_lang(tc.ui_language),
        "answer_language": get_lang(tc.answer_language),
        "nationality_country_code": tc.nationality_country_code,
        "origin_country_code": tc.origin_country_code,
        "origin_city_or_airport": tc.origin_city_or_airport,
        "destination_country_code": tc.destination_country_code,
        "destination_city_or_airport": tc.destination_city_or_airport,
        "trip_type": tc.trip_type,
        "departure_date": tc.departure_date,
        "return_date": tc.return_date,
        "airline_code": tc.airline_code,
        "cabin": tc.cabin,
        "purpose": tc.purpose,
    }


@router.get("/{chat_id}")
async def get_trip_context(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_authenticated_user),
):
    try:
        chat_uuid = uuid.UUID(chat_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chat_id")

    result = await db.execute(
        select(TripContextORM).where(TripContextORM.chat_id == chat_uuid)
    )
    trip_context = result.scalar_one_or_none()

    if not trip_context:
        return {"trip_context": None}

    return {"trip_context": serialize_trip_context(trip_context)}


@router.put("/{chat_id}")
async def update_trip_context(
    chat_id: str,
    trip_context_request: TripContext,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_authenticated_user),
):
    try:
        chat_uuid = uuid.UUID(chat_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chat_id")

    result = await db.execute(
        select(TripContextORM).where(TripContextORM.chat_id == chat_uuid)
    )
    trip_context = result.scalar_one_or_none()

    if trip_context:
        # Update
        trip_context.ui_language = Language[trip_context_request.ui_language]
        trip_context.answer_language = Language[trip_context_request.answer_language]
        trip_context.nationality_country_code = (
            trip_context_request.nationality_country_code
        )
        trip_context.origin_country_code = trip_context_request.origin_country_code
        trip_context.origin_city_or_airport = (
            trip_context_request.origin_city_or_airport
        )
        trip_context.destination_country_code = (
            trip_context_request.destination_country_code
        )
        trip_context.destination_city_or_airport = (
            trip_context_request.destination_city_or_airport
        )
        trip_context.trip_type = trip_context_request.trip_type
        trip_context.departure_date = trip_context_request.departure_date
        trip_context.return_date = trip_context_request.return_date
        trip_context.airline_code = trip_context_request.airline_code
        trip_context.cabin = trip_context_request.cabin
        trip_context.purpose = trip_context_request.purpose
    else:
        # Create
        trip_context = TripContextORM(
            chat_id=chat_uuid,
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
        db.add(trip_context)

    await db.commit()

    return {"trip_context": serialize_trip_context(trip_context)}


@router.delete("/{chat_id}")
async def delete_trip_context(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_authenticated_user),
):
    try:
        chat_uuid = uuid.UUID(chat_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chat_id")

    result = await db.execute(
        select(TripContextORM).where(TripContextORM.chat_id == chat_uuid)
    )
    trip_context = result.scalar_one_or_none()

    if not trip_context:
        raise HTTPException(status_code=404, detail="Trip context not found")

    await db.delete(trip_context)
    await db.commit()

    return {"success": True}

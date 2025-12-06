import httpx
from typing import Optional, Dict
from app.config import get_settings

settings = get_settings()

RAPIDAPI_HOST = settings["rapid_apihost"]

HEADERS = {
    "x-rapidapi-key": settings["rapid_apikey"],
    "x-rapidapi-host": RAPIDAPI_HOST,
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "AirMini/1.0",
}


async def check_visa_requirements(
    passport_country: str, destination_country: str
) -> Optional[Dict]:
    url = f"https://{RAPIDAPI_HOST}/v2/visa/check"
    payload = (
        f"passport={passport_country.upper()}&destination={destination_country.upper()}"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=HEADERS, content=payload, timeout=10.0
            )
            if response.status_code == 200:
                print(f" Visa API success: {passport_country} → {destination_country}")
                return response.json()
    except Exception as e:
        print(f"Visa API exception: {e}")
        return None

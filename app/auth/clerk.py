from typing import Optional, Dict

from fastapi import Request, Depends, HTTPException, status
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions

from app.config import get_settings

settings = get_settings()

# Clerk backend SDK
sdk = Clerk(bearer_auth=settings["clerk_secretKey"])

NOT_AUTHORIZED = "Not Authorized"


def _has_clerk_auth(request: Request) -> bool:
    return "authorization" in request.headers or "__session" in request.cookies


def _authenticate_and_get_user_details(request: Request) -> Dict[str, str]:
    try:
        request_state = sdk.authenticate_request(
            request,
            AuthenticateRequestOptions(
                authorized_parties=[
                    "http://localhost:3000",
                    "https://airmini-frontend.vercel.app",
                ],
            ),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=NOT_AUTHORIZED,
        )

    if not request_state.is_signed_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=NOT_AUTHORIZED,
        )

    user_id = request_state.payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=NOT_AUTHORIZED,
        )

    return {"user_id": user_id}


async def get_optional_user(request: Request) -> Optional[dict]:
    if not _has_clerk_auth(request):
        return None

    return _authenticate_and_get_user_details(request)


async def get_authenticated_user(
    user: Optional[dict] = Depends(get_optional_user),
) -> dict:

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=NOT_AUTHORIZED,
        )
    return user

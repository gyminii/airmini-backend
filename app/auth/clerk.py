from typing import Dict, Optional
from clerk_backend_api import Clerk
from fastapi import Request, HTTPException, status
from app.config import get_settings
from clerk_backend_api.security.types import AuthenticateRequestOptions

settings = get_settings()

sdk = Clerk(bearer_auth=settings["clerk_secretKey"])

NOT_AUTHORIZED = "Not Authorized"


async def authenticate_and_get_user_details(request: Request):
    try:
        request_state = sdk.authenticate_request(
            request,
            AuthenticateRequestOptions(
                authorized_parties=["http://localhost:3000"],
                jwt_key=settings["jwt_key"],
            ),
        )
        if not request_state.is_signed_in:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=NOT_AUTHORIZED
            )
        user_id = request_state.payload.get("sub")
        return {"user_id": user_id}
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid Credentials",
        )


async def get_current_user(request: Request) -> Optional[dict]:
    try:
        return await authenticate_and_get_user_details(request)
    except:
        return None

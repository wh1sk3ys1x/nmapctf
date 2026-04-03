from typing import Annotated

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db

DbSession = Annotated[Session, Depends(get_db)]


def get_current_api_user(
    db: DbSession,
    authorization: str = Header(default=""),
):
    """Extract and validate JWT bearer token from Authorization header."""
    from app.auth import decode_access_token
    from app.models import User

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    token = authorization[7:]
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user


CurrentUser = Annotated["User", Depends(get_current_api_user)]

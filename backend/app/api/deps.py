from typing import Optional
from fastapi import Header, HTTPException, status
from ..config import settings


def verify_device_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """Validate X-API-Key header against configured DEVICE_API_KEY."""
    if not x_api_key or x_api_key != settings.DEVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing device API key",
        )
    return x_api_key


def verify_frontend_token(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_frontend_token: Optional[str] = Header(None, alias="X-Frontend-Token"),
) -> str:
    """Validate frontend bearer token or X-Frontend-Token header against FRONTEND_API_TOKEN."""
    token = None
    if authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        else:
            token = authorization
    elif x_frontend_token:
        token = x_frontend_token

    if not token or token != settings.FRONTEND_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing frontend authentication token",
        )
    return token

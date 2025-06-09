from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasicCredentials
from discord_agents.core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    security,
)
from discord_agents.core.config import settings

router = APIRouter()


@router.post("/login")
async def login(
    credentials: HTTPBasicCredentials = Depends(security),
) -> dict[str, str]:
    """Login endpoint"""
    if not authenticate_user(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": credentials.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def read_users_me(
    current_user: str = Depends(get_current_user),
) -> dict[str, str]:
    """Get current user info"""
    return {"username": current_user}

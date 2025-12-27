import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import ValidationError
from starlette import status

from src.users.adapters.dto_models.token import TokenData
from src.users.adapters.dto_models.users import UserData
from src.users.adapters.repository.user_repository import UserRepository

SECRET_KEY = os.getenv("JWT_SECRET", "75f2a97a1dbba8638c4a476881ae4809add2798f7f2c11b7d640e9e352bcce14")
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

password_hash = PasswordHash.recommended()
user_repo = UserRepository()


def verify_password(plain_password: str | bytes, hashed_password: str | bytes) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str | bytes) -> str:
    return password_hash.hash(password)


async def authenticate_user(username: str, password: str) -> UserData | None:
    user = await user_repo.get_user_by_username(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return UserData(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        hashed_password="",
    )


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> UserData:
    authenticate_value = (
        f'Bearer scope="{security_scopes.scope_str}"'
        if security_scopes.scopes
        else "Bearer"
    )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, username=username)
    except (InvalidTokenError, ValidationError) as e:
        raise credentials_exception from e
    user = await user_repo.get_user_by_username(username)
    if user is None:
        raise credentials_exception

    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )

    return UserData(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        hashed_password="",
    )


async def get_current_active_user(current_user: Annotated[UserData, Depends(get_current_user)]) -> UserData:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

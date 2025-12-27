from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.users.adapters.models.users import UserDocument


class TokenResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105


class UserResponseSchema(BaseModel):
    user_id: UUID
    username: str
    email: str | None


class UsersResponseSchema(BaseModel):
    users: list[UserResponseSchema]

    @classmethod
    def from_odm(cls, users: list[UserDocument]) -> Self:
        return cls(users=[UserResponseSchema(
            user_id=user.user_id,
            username=user.username,
            email = user.email,
        ) for user in users])

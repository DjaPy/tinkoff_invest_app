from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from beanie import Document, Indexed
from pydantic import Field


class TokenDocument(Document):
    access_token: str
    token_type: str


class UserDocument(Document):
    user_id: UUID = Field(default_factory=uuid4)
    username: Annotated[str, Indexed(unique=True)]
    email: Annotated[str | None, Indexed(unique=True)]
    hashed_password: str
    full_name: str | None = None
    disabled: bool | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = 'users'

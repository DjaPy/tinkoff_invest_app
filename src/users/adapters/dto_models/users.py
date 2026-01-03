from dataclasses import dataclass
from uuid import UUID


@dataclass
class UserData:
    username: str
    hashed_password: str
    user_id: UUID
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = True


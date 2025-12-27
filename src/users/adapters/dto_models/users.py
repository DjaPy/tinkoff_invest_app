from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class UserData:
    username: str
    hashed_password: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = True
    user_id: UUID | None = field(default=None)

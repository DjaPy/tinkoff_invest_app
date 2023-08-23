from datetime import datetime
from uuid import UUID

from odmantic import Model, Field
from pydantic import validator

from tinkoff.invest import AccessLevel, AccountStatus, AccountType


class SandboxAccount(Model):
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    account_id: str
    type: AccountType
    name: str
    status: AccountStatus
    opened_date: datetime
    closed_date: datetime
    access_level: AccessLevel

    class Config:
        collection = "accounts"

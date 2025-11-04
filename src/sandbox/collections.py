from datetime import datetime

from beanie import Document
from tinkoff.invest import AccessLevel, AccountStatus, AccountType


class SandboxAccount(Document):
    created_at: datetime
    updated_at: datetime

    account_id: str
    type: AccountType
    name: str
    status: AccountStatus
    opened_date: datetime
    closed_date: datetime
    access_level: AccessLevel

    class Settings:
        name = 'sandbox_accounts'


all_collections = (SandboxAccount, )

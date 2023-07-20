from datetime import datetime

from odmantic import Model

from src.enums import AccessLevelEnum, AccountStatusEnum, AccountTypeEnum


class BaseCollections(Model):
    created_at: datetime
    deleted_at: datetime


class SandboxAccount(BaseCollections):
    account_id: str
    type: AccountTypeEnum
    name: str
    status: AccountStatusEnum
    opened_date: datetime
    closed_date: datetime
    access_level: AccessLevelEnum

    class Config:
        collection = "accounts"

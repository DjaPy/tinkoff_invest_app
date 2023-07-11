from datetime import datetime

from odmantic import Model


class BaseCollections(Model):
    created_at: datetime
    deleted_at: datetime


class SandboxAccount(BaseCollections):
    account_id: str

    class Config:
        collection = "sandbox_accounts"

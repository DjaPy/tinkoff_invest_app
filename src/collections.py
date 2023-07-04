from datetime import datetime

from odmantic import Model


class SandboxAccount(Model):
    account_id: str
    created_at: datetime
    deleted_at: datetime

    class Config:
        collection = "sandbox_accounts"

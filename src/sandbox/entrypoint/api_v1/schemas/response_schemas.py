from pydantic import BaseModel

from src.sandbox.collections import SandboxAccount


class AccountsSandboxResponse(BaseModel):
    accounts: list[SandboxAccount]

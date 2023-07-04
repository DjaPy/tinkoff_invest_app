from pydantic import BaseModel


class CreateAccountSandboxResponse(BaseModel):
    account_id: str

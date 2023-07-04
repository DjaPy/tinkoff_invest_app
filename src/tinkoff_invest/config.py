from pydantic import BaseModel


class TinkoffInvestSettings(BaseModel):
    token: str
    sandbox_token: str | None
    app_name: str | None
    context_name: str | None

from pydantic import BaseModel


class TinkoffInvestSettings(BaseModel):
    token: str
    sandbox_token: str | None = None
    app_name: str | None = None
    context_name: str | None = None

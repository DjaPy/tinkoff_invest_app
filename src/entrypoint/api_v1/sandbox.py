from aiomisc import get_context
from fastapi import APIRouter

from tinkoff.invest.async_services import AsyncServices

from src.consts import TINKOFF_INVEST
from src.entrypoint.api_v1.schemas.response_schemas import CreateAccountSandboxResponse

sandbox_router = APIRouter(prefix="/sandbox", tags=['sandbox'])


@sandbox_router.post(
    path="/",
)
async def create_sandbox_account() -> CreateAccountSandboxResponse:
    invest_client: AsyncServices = await get_context()[TINKOFF_INVEST]
    account_sandbox = await invest_client.sandbox.open_sandbox_account()
    await save_account_sandbox(account_sandbox.account_id)
    return CreateAccountSandboxResponse(account_id=account_sandbox.account_id)

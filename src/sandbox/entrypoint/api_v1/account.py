from aiomisc import get_context
from fastapi import APIRouter
from tinkoff.invest.async_services import AsyncServices

from src.consts import TINKOFF_INVEST
from src.sandbox.access_layer.sandbox.account import (
    get_account_sandbox_data_by_account_id,
    get_all_accounts_sandbox,
    save_account_sandbox,
)
from src.sandbox.collections import SandboxAccount
from src.sandbox.entrypoint.api_v1.schemas.response_schemas import AccountsSandboxResponse

account_router = APIRouter(prefix='/account')


@account_router.post(path='/', response_model=SandboxAccount)
async def create_sandbox_account() -> SandboxAccount:
    invest_client: AsyncServices = await get_context()[TINKOFF_INVEST]
    await invest_client.sandbox.open_sandbox_account()
    accounts_resp = await invest_client.sandbox.get_sandbox_accounts()
    await save_account_sandbox(accounts_resp.accounts)
    return await get_account_sandbox_data_by_account_id(accounts_resp.accounts[0].id)


@account_router.get(path='/{account_id}', response_model=SandboxAccount)
async def get_sandbox_account_by_account_id(account_id: str) -> SandboxAccount:
    return await get_account_sandbox_data_by_account_id(account_id)


@account_router.get(path='/', response_model=AccountsSandboxResponse)
async def get_sandbox_accounts() -> AccountsSandboxResponse:
    accounts = await get_all_accounts_sandbox()
    return AccountsSandboxResponse(accounts=accounts)

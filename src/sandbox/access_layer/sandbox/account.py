from dataclasses import asdict
from datetime import datetime

from aiomisc import get_context
from odmantic import ObjectId
from tinkoff.invest import GetAccountsResponse

from src.consts import MONGO_DB
from src.sandbox.collections import SandboxAccount


async def save_account_sandbox(accounts: GetAccountsResponse) -> None:
    engine = await get_context()[MONGO_DB]
    accounts_db = await engine.find(SandboxAccount, sort=SandboxAccount.account_id)
    accounts_ids = [account.account_id for account in accounts_db]
    account_dicts = [asdict(account_proto) for account_proto in accounts.accounts if account_proto.id not in accounts_ids]
    accounts = [SandboxAccount.parse_obj(account | {'account_id': account.pop('id')}) for account in account_dicts]
    await engine.save_all(accounts)


async def get_all_accounts_sandbox() -> list[SandboxAccount]:
    engine = await get_context()[MONGO_DB]
    return await engine.find(SandboxAccount)


async def get_account_sandbox_data_by_account_id(account_id: str) -> SandboxAccount:
    engine = await get_context()[MONGO_DB]
    return await engine.find_one(SandboxAccount, SandboxAccount.account_id == account_id)


async def get_account_sandbox_data_by_id(id_: ObjectId) -> SandboxAccount:
    engine = await get_context()[MONGO_DB]
    return await engine.find_one(SandboxAccount, SandboxAccount.id == id_)

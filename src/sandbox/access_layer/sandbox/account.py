from dataclasses import asdict

from aiomisc import get_context
from bson import ObjectId
from tinkoff.invest import GetAccountsResponse, Account

from src.consts import MONGO_DB
from src.sandbox.collections import SandboxAccount


async def save_account_sandbox(accounts: list[Account]) -> None:
    engine = await get_context()[MONGO_DB]
    accounts_db = await engine.find(SandboxAccount, sort=SandboxAccount.account_id)
    accounts_ids = [account.account_id for account in accounts_db]
    account_dicts = [
        asdict(account_proto)
        for account_proto in accounts
        if account_proto.id not in accounts_ids
    ]
    new_accounts = [
        SandboxAccount(**(account | {"account_id": account.pop("id")}))
        for account in account_dicts
    ]
    await engine.save_all(new_accounts)


async def get_all_accounts_sandbox() -> list[SandboxAccount]:
    client = await get_context()[MONGO_DB]
    async with await client.start_session() as session:
        result = SandboxAccount.find_many(session=session)
        return await result.to_list()


async def get_account_sandbox_data_by_account_id(account_id: str) -> SandboxAccount:
    engine = await get_context()[MONGO_DB]
    return await engine.find_one(
        SandboxAccount, SandboxAccount.account_id == account_id
    )


async def get_account_sandbox_data_by_id(id_: ObjectId) -> SandboxAccount:
    engine = await get_context()[MONGO_DB]
    return await engine.find_one(SandboxAccount, SandboxAccount.id == id_)

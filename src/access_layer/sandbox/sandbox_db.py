from aiomisc import get_context

from src.collections import SandboxAccount
from src.consts import MONGO_DB


async def save_account_sandbox(account_id: str) -> None:
    account = SandboxAccount(account_id=account_id)
    engine = await get_context()[MONGO_DB]
    await engine.save(account)

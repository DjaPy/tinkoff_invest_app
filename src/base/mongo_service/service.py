from aiomisc import Service
from beanie import init_beanie
from motor.core import AgnosticClient
from motor.motor_asyncio import AsyncIOMotorClient

from src.algo_trading.adapters.models import BEANIE_MODELS
from src.base.mongo_service.config import MongoDBSettings
from src.sandbox.collections import SandboxAccount


class MongoDBService(Service):

    _client: AgnosticClient
    _context_name: str

    def __init__(
        self,
        settings: MongoDBSettings,
        context_name: str = 'mongodb',
    ) -> None:
        super().__init__()
        self.settings = settings
        self._context_name = context_name

    async def start(self) -> None:
        self._client = AsyncIOMotorClient(str(self.settings.dsn))
        await init_beanie(
            database=self._client[self.settings.db_name],
            document_models=[SandboxAccount, *BEANIE_MODELS],  # type: ignore
        )
        self.context[self._context_name] = self._client

    async def stop(self, exception: Exception | None = None) -> None:
        self._client.close()

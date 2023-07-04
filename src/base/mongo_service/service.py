from aiomisc import Service
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine

from src.base.mongo_service.config import MongoDBSettings


class MongoDBService(Service):

    _client: AsyncIOMotorClient
    _mongo_engine: AIOEngine
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
        self._client = AsyncIOMotorClient(self.settings.dsn)
        self._mongo_engine = AIOEngine(client=self._client, database=self.settings.db_name)
        self.context[self._context_name] = self._mongo_engine

    async def stop(self, exception: Exception | None = None) -> None:
        self._client.close()

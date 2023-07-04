from tinkoff.invest import AsyncClient

from aiomisc import Service

from src.tinkoff_invest.config import TinkoffInvestSettings
from tinkoff.invest.constants import INVEST_GRPC_API_SANDBOX


class TinkoffInvestService(Service):
    _client: AsyncClient

    def __init__(self, settings: TinkoffInvestSettings, context_name: str) -> None:
        super().__init__()
        self._settings = settings
        self._context_name = context_name

    async def start(self) -> None:
        self._client = AsyncClient(
            token=self._settings.token,
            target=INVEST_GRPC_API_SANDBOX,
            sandbox_token=self._settings.sandbox_token,
        )
        await self._client.__aenter__()
        self.context[self._context_name] = self._client

    async def stop(self, except_=None) -> None:
        await self._client.__aexit__(self, None, None)

    @property
    def tinkoff_invest(self) -> AsyncClient:
        return self._client

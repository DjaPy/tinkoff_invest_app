import pytest

from src.base.consts import FASTAPI
from src.algo_trading.ports.api.v1 import analytics_router, orders_router, positions_router, strategies_router
from src.base.fastapi_service import FastAPIService


@pytest.fixture
async def services(monkeypatch, config, unused_tcp_port):
    monkeypatch.setattr(config.http, 'port', unused_tcp_port)
    fastapi_service = FastAPIService(
        settings=config.http,
        app_name='test',
        context_name=FASTAPI,
        routers=[analytics_router, orders_router, positions_router, strategies_router],
    )
    return [fastapi_service]

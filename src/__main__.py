import asyncio

from aiomisc import entrypoint

from src.algo_trading.ports.api.v1 import analytics_router, orders_router, positions_router, strategies_router
from src.algo_trading.services.scheduled_metrics import ScheduledMetricsService
from src.base.fastapi_service import FastAPIService
from src.base.mongo_service.service import MongoDBService
from src.base.tinkoff_invest.service import TinkoffInvestServiceSandbox
from src.config import config
from src.consts import FASTAPI_SERVICE, MONGO_DB, TINKOFF_INVEST_SANDBOX
from src.sandbox.entrypoint.api_v1.account import account_router

fastapi_service = FastAPIService(settings=config.http, context_name=FASTAPI_SERVICE, app_name=config.app_name)
tinkoff_invest_sandbox = TinkoffInvestServiceSandbox(
    settings=config.tinkoff_invest,
    context_name=TINKOFF_INVEST_SANDBOX,
)
mongo_service = MongoDBService(settings=config.mongo_db, context_name=MONGO_DB)
scheduled_metrics_service = ScheduledMetricsService(run_at_startup=False)


if __name__ == '__main__':
    with entrypoint(
        fastapi_service,
        mongo_service,
        tinkoff_invest_sandbox,
        scheduled_metrics_service,
        log_level='info',
        log_format='color',
        log_buffering=True,
        log_buffer_size=1024,
        log_flush_interval=0.2,
        log_config=True,
        policy=asyncio.DefaultEventLoopPolicy(),
        debug=False,
    ) as loop:
        # Register existing routers
        fastapi_service.fastapi.include_router(account_router)

        # Register algo_trading routers
        fastapi_service.fastapi.include_router(strategies_router)
        fastapi_service.fastapi.include_router(orders_router)
        fastapi_service.fastapi.include_router(positions_router)
        fastapi_service.fastapi.include_router(analytics_router)

        loop.run_forever()

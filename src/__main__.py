import asyncio

from aiomisc import entrypoint

from src.base.fastapi_service import FastAPIService
from src.base.mongo_service.service import MongoDBService
from src.config import config
from src.consts import FASTAPI_SERVICE, MONGO_DB, TINKOFF_INVEST
from src.sandbox.entrypoint.api_v1.account import account_router
from src.tinkoff_invest.service import TinkoffInvestService

fastapi_service = FastAPIService(settings=config.http, context_name=FASTAPI_SERVICE, app_name=config.app_name)
tinkoff_invest_service = TinkoffInvestService(settings=config.tinkoff_invest, context_name=TINKOFF_INVEST)
mongo_service = MongoDBService(settings=config.mongo_db, context_name=MONGO_DB)


if __name__ == '__main__':
    with entrypoint(
        fastapi_service,
        mongo_service,
        tinkoff_invest_service,
        log_level="info",
        log_format="color",
        log_buffering=True,
        log_buffer_size=1024,
        log_flush_interval=0.2,
        log_config=True,
        policy=asyncio.DefaultEventLoopPolicy(),
        debug=False
    ) as loop:
        fastapi_service.fastapi.include_router(account_router)
        loop.run_forever()

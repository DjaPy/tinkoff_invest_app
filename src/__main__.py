import logging

from aiomisc import entrypoint

from algo_trading.adapters.models import (
    MarketDataDocument,
    PerformanceMetricsDocument,
    PortfolioPositionDocument,
    TinkoffAccountDocument,
    TradeOrderDocument,
    TradingSessionDocument,
    TradingStrategyDocument,
)
from sandbox.collections import SandboxAccount
from src.algo_trading.ports.api.v1 import (
    analytics_router,
    orders_router,
    positions_router,
    strategies_router,
)
from src.algo_trading.ports.api.v1.tinkoff_accounts import tinkoff_accounts_router
from src.algo_trading.services.scheduled_metrics import ScheduledMetricsService
from src.base.fastapi_service import FastAPIService
from src.base.mongo_service.service import MongoDBService
from src.base.tinkoff_invest.service import TinkoffInvestServiceSandbox
from src.config import config
from src.consts import FASTAPI_SERVICE, MONGO_DB, TINKOFF_INVEST_SANDBOX
from src.sandbox.entrypoint.api_v1.account import account_router
from src.users.ports.api.v1.auth import auth_router
from src.users.ports.api.v1.users import users_router
from users.adapters.models.users import UserDocument

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

BEANIE_MODELS = [
    TinkoffAccountDocument,
    TradingStrategyDocument,
    TradeOrderDocument,
    MarketDataDocument,
    PortfolioPositionDocument,
    PerformanceMetricsDocument,
    TradingSessionDocument,
    SandboxAccount,
    UserDocument,
]

fastapi_service = FastAPIService(
    settings=config.http,
    context_name=FASTAPI_SERVICE,
    app_name=config.app_name,
    routers=[
        analytics_router,
        account_router,
        orders_router,
        positions_router,
        strategies_router,
        tinkoff_accounts_router,
        auth_router,
        users_router,
    ],
)
tinkoff_invest_sandbox = TinkoffInvestServiceSandbox(
    settings=config.tinkoff_invest,
    context_name=TINKOFF_INVEST_SANDBOX,
)
mongo_service = MongoDBService(settings=config.mongo_db, models=BEANIE_MODELS, context_name=MONGO_DB)
scheduled_metrics_service = ScheduledMetricsService(run_at_startup=False)

logger.info('Inits all dependencies')


if __name__ == '__main__':
    with entrypoint(
        fastapi_service,
        mongo_service,
        tinkoff_invest_sandbox,
        scheduled_metrics_service,
        log_level='info',
        log_format='color',
    ) as loop:
        logger.info('Starting Tinkoff Invest Service')
        loop.run_forever()

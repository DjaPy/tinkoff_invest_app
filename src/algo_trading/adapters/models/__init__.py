"""Beanie ODM Models for Algorithmic Trading - Hexagonal Architecture Adapters."""
from src.algo_trading.enums import (
    OrderSideEnum,
    OrderStatusEnum,
    OrderTypeEnum,
    StrategyStatusEnum,
    StrategyTypeEnum,
)
from src.algo_trading.adapters.models.market_data import MarketDataDocument
from src.algo_trading.adapters.models.metrics import PerformanceMetricsDocument
from src.algo_trading.adapters.models.order import TradeOrderDocument
from src.algo_trading.adapters.models.position import PortfolioPositionDocument
from src.algo_trading.adapters.models.session import TradingSessionDocument
from src.algo_trading.adapters.models.strategy import (
    ArbitrageParameters,
    MarketMakingParameters,
    MeanReversionParameters,
    MomentumParameters,
    RiskControls,
    TradingStrategyDocument,
)


BEANIE_MODELS = [
    TradingStrategyDocument,
    TradeOrderDocument,
    MarketDataDocument,
    PortfolioPositionDocument,
    PerformanceMetricsDocument,
    TradingSessionDocument,
]
__all__ = [
    'ArbitrageParameters',
    'MarketDataDocument',
    'MarketMakingParameters',
    'MeanReversionParameters',
    'MomentumParameters',
    'OrderSideEnum',
    'OrderStatusEnum',
    'OrderTypeEnum',
    'PerformanceMetricsDocument',
    'PortfolioPositionDocument',
    'RiskControls',
    'StrategyStatusEnum',
    'StrategyTypeEnum',
    'TradeOrderDocument',
    'TradingSessionDocument',
    'TradingStrategyDocument',
]

from enum import StrEnum


class PeriodEnum(StrEnum):
    day = '1d'
    week = '1w'
    month = '1m'
    quarter = '3m'
    year = '1y'
    custom = 'custom'
    all = 'all'


class StrategyTypeEnum(StrEnum):
    """Trading strategy types."""

    MOMENTUM = 'momentum'
    MEAN_REVERSION = 'mean_reversion'
    ARBITRAGE = 'arbitrage'
    MARKET_MAKING = 'market_making'


class StrategyStatusEnum(StrEnum):
    """Strategy execution status."""

    INACTIVE = 'inactive'
    ACTIVE = 'active'
    PAUSED = 'paused'
    STOPPED = 'stopped'
    ERROR = 'error'


class OrderTypeEnum(StrEnum):
    """Order type enumeration."""

    MARKET = 'market'
    LIMIT = 'limit'
    STOP_LOSS = 'stop_loss'
    TAKE_PROFIT = 'take_profit'


class OrderSideEnum(StrEnum):
    """Order side enumeration."""

    BUY = 'buy'
    SELL = 'sell'


class OrderStatusEnum(StrEnum):
    """Order execution status."""

    PENDING = 'pending'
    SUBMITTED = 'submitted'
    FILLED = 'filled'
    PARTIALLY_FILLED = 'partially_filled'
    CANCELLED = 'cancelled'
    REJECTED = 'rejected'


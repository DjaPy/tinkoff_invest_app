"""TradingStrategy Beanie model - Hexagonal Architecture Adapter."""

from datetime import datetime, UTC
from decimal import Decimal
from uuid import UUID, uuid4

import pymongo
from beanie import Document
from pydantic import BaseModel, Field, ValidationInfo, field_validator

from src.algo_trading.adapters.models.common import DecimalField
from src.algo_trading.enums import StrategyStatusEnum, StrategyTypeEnum

MAX_PERIOD = 200
MIN_MOVING_AVERAGE = 5
MAX_STD_DEV_THRESHOLD = 5


class MomentumParameters(BaseModel):
    """Parameters for Momentum strategy."""

    lookback_period: int = Field(ge=1, le=200, description='Lookback period for momentum calculation')
    momentum_threshold: float = Field(ge=0, le=1, description='Threshold for momentum signal (0-1)')
    instruments: list[str] = Field(min_length=1, description='List of instruments to trade')
    position_size: float = Field(gt=0, description='Position size per instrument')


class MeanReversionParameters(BaseModel):
    """Parameters for Mean Reversion strategy."""

    moving_average_period: int = Field(ge=5, le=200, description='Period for moving average calculation')
    std_dev_threshold: float = Field(ge=0, le=5, description='Standard deviation threshold for entry signal')
    instruments: list[str] = Field(min_length=1, description='List of instruments to trade')


class ArbitrageParameters(BaseModel):
    """Parameters for Arbitrage strategy."""

    instrument_pairs: list[list[str]] = Field(
        min_length=1, description='Pairs of instruments for arbitrage (e.g., [["AAPL", "AAPL.US"]])',
    )
    spread_threshold: float = Field(ge=0, description='Minimum spread to execute arbitrage')


class MarketMakingParameters(BaseModel):
    """Parameters for Market Making strategy."""

    bid_ask_spread: float = Field(gt=0, description='Target bid-ask spread')
    inventory_limits: dict[str, int] = Field(description='Inventory limits per instrument')
    instruments: list[str] = Field(min_length=1, description='List of instruments for market making')


class RiskControls(BaseModel):
    """Risk management controls embedded in strategy."""

    max_position_size: DecimalField = Field(description='Maximum position size per instrument')
    max_portfolio_value: DecimalField = Field(description='Maximum total portfolio value')
    stop_loss_percent: DecimalField = Field(description='Stop-loss threshold (0.05 = 5%)', ge=0, le=1)
    max_drawdown_percent: DecimalField = Field(description='Maximum drawdown before halt', ge=0, le=1)
    daily_loss_limit: DecimalField = Field(description='Daily loss limit in currency', gt=0)
    max_orders_per_day: int = Field(description='Maximum orders per trading day', gt=0)
    trading_hours_start: str = Field(description='Trading start time (HH:MM:SS)')
    trading_hours_end: str = Field(description='Trading end time (HH:MM:SS)')
    enabled: bool = Field(default=True, description='Risk controls active flag')

    @field_validator('stop_loss_percent', 'max_drawdown_percent')
    @classmethod
    def validate_percentage(cls, v: Decimal) -> Decimal:
        """Ensure percentages are between 0 and 1."""
        if not (Decimal('0') <= v <= Decimal('1')):
            raise ValueError('Percentage must be between 0 and 1')
        return v


class TradingStrategyDocument(Document):
    """
    Algorithmic trading strategy configuration.

    Represents a strategy with parameters, risk controls, and execution state.
    Follows Hexagonal Architecture as an Adapter (infrastructure layer).
    """

    strategy_id: UUID = Field(default_factory=uuid4, description='Unique strategy identifier')
    name: str = Field(min_length=1, max_length=200, description='Strategy name')
    strategy_type: StrategyTypeEnum = Field(description='Type of trading strategy')
    status: StrategyStatusEnum = Field(default=StrategyStatusEnum.INACTIVE, description='Current execution status')
    parameters: MomentumParameters | MeanReversionParameters |ArbitrageParameters | MarketMakingParameters = Field(
        description='Strategy-specific parameters',
    )
    risk_controls: RiskControls = Field(description='Risk management configuration')
    created_at: datetime = Field(default_factory=datetime.now, description='Creation timestamp')
    updated_at: datetime = Field(default_factory=datetime.now, description='Last update timestamp')
    created_by: UUID = Field(description='User identifier')

    @field_validator('parameters', mode='before')
    @classmethod
    def validate_parameters(cls, v: dict | BaseModel, info: ValidationInfo) -> BaseModel:
        """Validate and convert strategy parameters based on strategy type."""
        strategy_type = info.data.get('strategy_type')

        if isinstance(v, BaseModel):
            return v

        parameter_models = {
            StrategyTypeEnum.MOMENTUM: MomentumParameters,
            StrategyTypeEnum.MEAN_REVERSION: MeanReversionParameters,
            StrategyTypeEnum.ARBITRAGE: ArbitrageParameters,
            StrategyTypeEnum.MARKET_MAKING: MarketMakingParameters,
        }

        if strategy_type in parameter_models:
            return parameter_models[strategy_type](**v)

        raise ValueError(f'Unknown strategy type: {strategy_type}')

    def can_transition_to(self, new_status: StrategyStatusEnum) -> bool:
        """
        Check if status transition is valid.

        Valid transitions:
        - INACTIVE → ACTIVE
        - ACTIVE → PAUSED, STOPPED, ERROR
        - PAUSED → ACTIVE, STOPPED
        - STOPPED → INACTIVE
        """
        valid_transitions = {
            StrategyStatusEnum.INACTIVE: {StrategyStatusEnum.ACTIVE},
            StrategyStatusEnum.ACTIVE: {
                StrategyStatusEnum.PAUSED, StrategyStatusEnum.STOPPED, StrategyStatusEnum.ERROR,
            },
            StrategyStatusEnum.PAUSED: {StrategyStatusEnum.ACTIVE, StrategyStatusEnum.STOPPED},
            StrategyStatusEnum.STOPPED: {StrategyStatusEnum.INACTIVE},
            StrategyStatusEnum.ERROR: {StrategyStatusEnum.INACTIVE, StrategyStatusEnum.STOPPED},
        }

        return new_status in valid_transitions.get(self.status, set())

    def update_status(self, new_status: StrategyStatusEnum) -> None:
        """Update strategy status with validation."""
        if not self.can_transition_to(new_status):
            raise ValueError(f'Invalid status transition from {self.status} to {new_status}')

        self.status = new_status
        self.updated_at = datetime.now(tz=UTC)

    class Settings:
        name = 'trading_strategies'
        indexes = [
            'strategy_id',
            [('created_by', pymongo.ASCENDING), ('name', pymongo.ASCENDING)],  # Unique per user
            'status',
            [('created_at', pymongo.DESCENDING)],
        ]

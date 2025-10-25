"""TradingStrategy Beanie model - Hexagonal Architecture Adapter."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

import pymongo
from beanie import Document
from pydantic import BaseModel, Field, ValidationInfo, field_validator


class StrategyType(str, Enum):
    """Trading strategy types."""

    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    ARBITRAGE = "arbitrage"
    MARKET_MAKING = "market_making"


class StrategyStatus(str, Enum):
    """Strategy execution status."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class RiskControls(BaseModel):
    """Risk management controls embedded in strategy."""

    max_position_size: Decimal = Field(description="Maximum position size per instrument")
    max_portfolio_value: Decimal = Field(description="Maximum total portfolio value")
    stop_loss_percent: Decimal = Field(description="Stop-loss threshold (0.05 = 5%)", ge=0, le=1)
    max_drawdown_percent: Decimal = Field(description="Maximum drawdown before halt", ge=0, le=1)
    daily_loss_limit: Decimal = Field(description="Daily loss limit in currency", gt=0)
    max_orders_per_day: int = Field(description="Maximum orders per trading day", gt=0)
    trading_hours_start: str = Field(description="Trading start time (HH:MM:SS)")
    trading_hours_end: str = Field(description="Trading end time (HH:MM:SS)")
    enabled: bool = Field(default=True, description="Risk controls active flag")

    @field_validator("stop_loss_percent", "max_drawdown_percent")
    @classmethod
    def validate_percentage(cls, v: Decimal) -> Decimal:
        """Ensure percentages are between 0 and 1."""
        if not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError("Percentage must be between 0 and 1")
        return v


class TradingStrategy(Document):
    """
    Algorithmic trading strategy configuration.

    Represents a strategy with parameters, risk controls, and execution state.
    Follows Hexagonal Architecture as an Adapter (infrastructure layer).
    """

    strategy_id: UUID = Field(default_factory=uuid4, description="Unique strategy identifier")
    name: str = Field(min_length=1, max_length=200, description="Strategy name")
    strategy_type: StrategyType = Field(description="Type of trading strategy")
    status: StrategyStatus = Field(default=StrategyStatus.INACTIVE, description="Current execution status")
    parameters: dict[str, Decimal] = Field(default_factory=dict, description="Strategy-specific parameters")
    risk_controls: RiskControls = Field(description="Risk management configuration")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    created_by: str = Field(description="User identifier")

    @classmethod
    def _validate_required_keys(cls, v: dict, required_keys: set[str], strategy_type: str) -> None:
        """Validate that required keys are present."""
        missing_keys = required_keys - set(v.keys())
        if missing_keys:
            raise ValueError(f"Missing required parameters for {strategy_type}: {missing_keys}")

    @classmethod
    def _validate_momentum_params(cls, v: dict) -> None:
        """Validate momentum strategy parameters."""
        if "lookback_period" in v and not 1 <= v["lookback_period"] <= 200:
            raise ValueError("lookback_period must be between 1 and 200")
        if "momentum_threshold" in v and not 0 <= v["momentum_threshold"] <= 1:
            raise ValueError("momentum_threshold must be between 0 and 1")

    @classmethod
    def _validate_mean_reversion_params(cls, v: dict) -> None:
        """Validate mean reversion strategy parameters."""
        if "moving_average_period" in v and not 5 <= v["moving_average_period"] <= 200:
            raise ValueError("moving_average_period must be between 5 and 200")
        if "std_dev_threshold" in v and not 0 <= v["std_dev_threshold"] <= 5:
            raise ValueError("std_dev_threshold must be between 0 and 5")

    @classmethod
    def _validate_arbitrage_params(cls, v: dict) -> None:
        """Validate arbitrage strategy parameters."""
        if "spread_threshold" in v and v["spread_threshold"] < 0:
            raise ValueError("spread_threshold must be non-negative")

    @classmethod
    def _validate_market_making_params(cls, v: dict) -> None:
        """Validate market making strategy parameters."""
        if "bid_ask_spread" in v and v["bid_ask_spread"] <= 0:
            raise ValueError("bid_ask_spread must be positive")

    @field_validator("parameters", mode="after")
    @classmethod
    def validate_parameters(cls, v: dict, info: ValidationInfo) -> dict:
        """Validate strategy parameters based on strategy type."""
        strategy_type = info.data.get("strategy_type")

        validators = {
            StrategyType.MOMENTUM: (
                {"lookback_period", "momentum_threshold", "instruments", "position_size"},
                cls._validate_momentum_params,
            ),
            StrategyType.MEAN_REVERSION: (
                {"moving_average_period", "std_dev_threshold", "instruments"},
                cls._validate_mean_reversion_params,
            ),
            StrategyType.ARBITRAGE: (
                {"instrument_pairs", "spread_threshold"},
                cls._validate_arbitrage_params,
            ),
            StrategyType.MARKET_MAKING: (
                {"bid_ask_spread", "inventory_limits", "instruments"},
                cls._validate_market_making_params,
            ),
        }

        if strategy_type in validators:
            required_keys, validator = validators[strategy_type]
            cls._validate_required_keys(v, required_keys, str(strategy_type))
            validator(v)

        return v

    def can_transition_to(self, new_status: StrategyStatus) -> bool:
        """
        Check if status transition is valid.

        Valid transitions:
        - INACTIVE → ACTIVE
        - ACTIVE → PAUSED, STOPPED, ERROR
        - PAUSED → ACTIVE, STOPPED
        - STOPPED → INACTIVE
        """
        valid_transitions = {
            StrategyStatus.INACTIVE: {StrategyStatus.ACTIVE},
            StrategyStatus.ACTIVE: {StrategyStatus.PAUSED, StrategyStatus.STOPPED, StrategyStatus.ERROR},
            StrategyStatus.PAUSED: {StrategyStatus.ACTIVE, StrategyStatus.STOPPED},
            StrategyStatus.STOPPED: {StrategyStatus.INACTIVE},
            StrategyStatus.ERROR: {StrategyStatus.INACTIVE, StrategyStatus.STOPPED},
        }

        return new_status in valid_transitions.get(self.status, set())

    def update_status(self, new_status: StrategyStatus) -> None:
        """Update strategy status with validation."""
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid status transition from {self.status} to {new_status}"
            )

        self.status = new_status
        self.updated_at = datetime.utcnow()

    class Settings:
        name = "trading_strategies"
        indexes = [
            "strategy_id",
            [("created_by", pymongo.ASCENDING), ("name", pymongo.ASCENDING)],  # Unique per user
            "status",
            [("created_at", pymongo.DESCENDING)],  # Most recent first
        ]

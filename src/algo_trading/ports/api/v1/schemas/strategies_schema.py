from pydantic import BaseModel, Field

from src.algo_trading.adapters.models import RiskControls, StrategyType, TradingStrategy


class CreateStrategyRequestSchema(BaseModel):
    """Request schema for creating a new strategy."""

    name: str = Field(min_length=1, max_length=100, description='Strategy name')
    strategy_type: StrategyType = Field(description='Type of trading strategy')
    parameters: dict = Field(description='Strategy-specific parameters')
    risk_controls: RiskControls = Field(description='Risk management configuration')


class UpdateStrategyRequestSchema(BaseModel):
    """Request schema for updating a strategy."""

    name: str | None = Field(None, min_length=1, max_length=100, description='Strategy name')
    parameters: dict | None = Field(None, description='Strategy-specific parameters')
    risk_controls: RiskControls | None = Field(None, description='Risk management configuration')


class StrategyListResponseSchema(BaseModel):
    """Response schema for listing strategies."""

    strategies: list[TradingStrategy] = Field(description='List of trading strategies')
    total: int = Field(ge=0, description='Total number of strategies')

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.algo_trading.adapters.models import (
    ArbitrageParameters,
    MarketMakingParameters,
    MeanReversionParameters,
    MomentumParameters,
)
from src.algo_trading.adapters.models import RiskControls, StrategyStatusEnum, StrategyTypeEnum, TradingStrategyDocument

StrategyParameters = MomentumParameters | MeanReversionParameters |ArbitrageParameters | MarketMakingParameters

class CreateStrategyRequestSchema(BaseModel):
    """Request schema for creating a new strategy."""

    name: str = Field(min_length=1, max_length=100, description='Strategy name')
    strategy_type: StrategyTypeEnum = Field(description='Type of trading strategy')
    parameters: dict = Field(description='Strategy-specific parameters')
    risk_controls: RiskControls = Field(description='Risk management configuration')


class UpdateStrategyRequestSchema(BaseModel):
    """Request schema for updating a strategy."""

    name: str | None = Field(None, min_length=1, max_length=100, description='Strategy name')
    parameters: StrategyParameters | None = Field(None, description='Strategy-specific parameters')
    risk_controls: RiskControls | None = Field(None, description='Risk management configuration')


class TradingStrategyResponseSchema(BaseModel):
    """Response schema for a single trading strategy."""

    strategy_id: UUID = Field(description='Unique strategy identifier')
    name: str = Field(description='Strategy name')
    strategy_type: StrategyTypeEnum = Field(description='Type of trading strategy')
    status: StrategyStatusEnum = Field(description='Current execution status')
    parameters: StrategyParameters = Field(description='Strategy-specific parameters')
    risk_controls: RiskControls = Field(description='Risk management configuration')
    created_at: datetime = Field(description='Creation timestamp')
    updated_at: datetime = Field(description='Last update timestamp')
    created_by: UUID = Field(description='User identifier')

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def ensure_timezone_aware(cls, v: datetime | str) -> datetime:
        """Ensure datetime fields are always timezone-aware (UTC)."""
        if isinstance(v, str):
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        elif isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v
        return v

    @classmethod
    def from_document(cls, document: TradingStrategyDocument) -> 'TradingStrategyResponseSchema':
        """Convert TradingStrategyDocument to response schema."""
        return cls(
            strategy_id=document.strategy_id,
            name=document.name,
            strategy_type=document.strategy_type,
            status=document.status,
            parameters=document.parameters,
            risk_controls=document.risk_controls,
            created_at=document.created_at,
            updated_at=document.updated_at,
            created_by=document.created_by,
        )


class StrategyListResponseSchema(BaseModel):
    """Response schema for listing strategies."""

    strategies: list[TradingStrategyDocument] = Field(description='List of trading strategies')
    total: int = Field(ge=0, description='Total number of strategies')

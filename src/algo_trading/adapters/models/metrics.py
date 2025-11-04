"""PerformanceMetrics Beanie model - Hexagonal Architecture Adapter."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from src.algo_trading.adapters.models.common import DecimalField


class PerformanceMetricsDocument(Document):
    """
    Strategy performance statistics and risk measures.

    Calculated over a specific time period with returns, Sharpe ratio, drawdown, etc.
    Follows Hexagonal Architecture as an Adapter (infrastructure layer).
    """

    metrics_id: UUID = Field(default_factory=uuid4, description='Unique metrics identifier')
    strategy_id: UUID = Field(description='Strategy being measured')

    period_start: datetime = Field(description='Performance period start')
    period_end: datetime = Field(description='Performance period end')

    total_return: DecimalField = Field(description='Total return percentage (0.05 = 5%)')
    annualized_return: DecimalField = Field(description='Annualized return percentage')

    sharpe_ratio: DecimalField = Field(description='Risk-adjusted return (excess return / volatility)')
    max_drawdown: DecimalField = Field(description='Maximum peak-to-trough decline')
    volatility: DecimalField = Field(description='Return volatility (standard deviation)')

    win_rate: DecimalField = Field(ge=0, le=1, description='Percentage of profitable trades')
    profit_factor: DecimalField = Field(ge=0, description='Gross profit / gross loss ratio')
    trade_count: int = Field(ge=0, description='Number of trades in period')

    average_win: DecimalField = Field(default=Decimal('0'), description='Average winning trade')
    average_loss: DecimalField = Field(default=Decimal('0'), description='Average losing trade')
    largest_win: DecimalField = Field(default=Decimal('0'), description='Largest winning trade')
    largest_loss: DecimalField = Field(default=Decimal('0'), description='Largest losing trade')

    calculated_at: datetime = Field(default_factory=datetime.utcnow, description='Calculation timestamp')

    @field_validator('period_end', mode='after')
    @classmethod
    def validate_period(cls, v: datetime, values: ValidationInfo) -> datetime:
        """Period end must be after period start."""
        period_start = values.data.get('period_start')
        if period_start and v <= period_start:
            raise ValueError('period_end must be after period_start')
        return v

    @field_validator('total_return', 'annualized_return')
    @classmethod
    def validate_returns(cls, v: Decimal) -> Decimal:
        """Returns should be reasonable (-100% to +1000%)."""
        if not (Decimal('-1') <= v <= Decimal('10')):
            raise ValueError('Return seems unrealistic, check calculation')
        return v

    @field_validator('max_drawdown')
    @classmethod
    def validate_drawdown(cls, v: Decimal) -> Decimal:
        """Drawdown should be negative or zero."""
        if v > 0:
            raise ValueError('Max drawdown should be negative or zero')
        return v

    @field_validator('volatility')
    @classmethod
    def validate_volatility(cls, v: Decimal) -> Decimal:
        """Volatility must be non-negative."""
        if v < 0:
            raise ValueError('Volatility cannot be negative')
        return v

    @field_validator('sharpe_ratio')
    @classmethod
    def validate_sharpe(cls, v: Decimal) -> Decimal:
        """Sharpe ratio should be reasonable (-5 to +5)."""
        if not (Decimal('-5') <= v <= Decimal('5')):
            raise ValueError('Sharpe ratio seems unrealistic, check calculation')
        return v

    class Settings:
        name = 'performance_metrics'
        indexes = [
            'metrics_id',
            [('strategy_id', 1), ('period_end', -1)],  # Latest metrics first
            'calculated_at',
        ]

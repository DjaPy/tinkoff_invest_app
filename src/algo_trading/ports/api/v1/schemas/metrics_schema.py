from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.algo_trading.adapters.models.metrics import PerformanceMetricsDocument


class PerformanceMetricsResponseSchema(BaseModel):
    metrics_id: UUID = Field(description='Unique metrics identifier')
    strategy_id: UUID = Field(description='Strategy being measured')

    period_start: datetime = Field(description='Performance period start')
    period_end: datetime = Field(description='Performance period end')

    total_return: Decimal = Field(description='Total return percentage (0.05 = 5%)')
    annualized_return: Decimal = Field(description='Annualized return percentage')

    sharpe_ratio: Decimal = Field(description='Risk-adjusted return (excess return / volatility)')
    max_drawdown: Decimal = Field(description='Maximum peak-to-trough decline')
    volatility: Decimal = Field(description='Return volatility (standard deviation)')

    win_rate: Decimal = Field(description='Percentage of profitable trades')
    profit_factor: Decimal = Field(description='Gross profit / gross loss ratio')
    trade_count: int = Field(description='Number of trades in period')

    average_win: Decimal = Field(description='Average winning trade')
    average_loss: Decimal = Field(description='Average losing trade')
    largest_win: Decimal = Field(description='Largest winning trade')
    largest_loss: Decimal = Field(description='Largest losing trade')

    calculated_at: datetime = Field(description='Calculation timestamp')

    @classmethod
    def from_document(cls, document: PerformanceMetricsDocument) -> 'PerformanceMetricsResponseSchema':
        """Convert PerformanceMetricsDocument to response schema."""
        return cls(
            metrics_id=document.metrics_id,
            strategy_id=document.strategy_id,
            period_start=document.period_start,
            period_end=document.period_end,
            total_return=document.total_return,
            annualized_return=document.annualized_return,
            sharpe_ratio=document.sharpe_ratio,
            max_drawdown=document.max_drawdown,
            volatility=document.volatility,
            win_rate=document.win_rate,
            profit_factor=document.profit_factor,
            trade_count=document.trade_count,
            average_win=document.average_win,
            average_loss=document.average_loss,
            largest_win=document.largest_win,
            largest_loss=document.largest_loss,
            calculated_at=document.calculated_at,
        )

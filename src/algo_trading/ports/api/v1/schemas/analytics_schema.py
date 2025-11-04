from datetime import datetime, timedelta, UTC
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from starlette import status
from starlette.exceptions import HTTPException

from src.algo_trading.enums import PeriodEnum
from src.algo_trading.adapters.models import RiskControls, StrategyTypeEnum

def check_period(from_date: datetime | None, to_date: datetime | None, period: PeriodEnum | None) -> None:
    if period == PeriodEnum.custom and (from_date is None or to_date is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f'from_date and to_date are required when period={period}',
        )
    if period is None and (from_date is None or to_date is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f'from_date and to_date are required when period={period}',
        )

def calculate_period_dates(period: PeriodEnum | None) -> tuple[datetime, datetime]:
    end_date = datetime.now(tz=UTC)

    one_days = end_date - timedelta(days=1)

    delta_period_to_datetime = {
        PeriodEnum.day: one_days,
        PeriodEnum.week: end_date - timedelta(weeks=1),
        PeriodEnum.month: end_date - timedelta(days=30),
        PeriodEnum.quarter: end_date - timedelta(days=90),
        PeriodEnum.year: end_date - timedelta(days=365),
        None : one_days,
    }


    start_date = delta_period_to_datetime.get(period, one_days)

    return start_date, end_date


class TradeAnalyticsResponseSchema(BaseModel):
    """Trade analytics response schema."""

    strategy_id: UUID = Field(description='Strategy identifier')
    period_start: datetime = Field(description='Analysis period start')
    period_end: datetime = Field(description='Analysis period end')
    total_trades: int = Field(ge=0, description='Total number of trades')
    winning_trades: int = Field(ge=0, description='Number of profitable trades')
    losing_trades: int = Field(ge=0, description='Number of losing trades')
    avg_win: Decimal = Field(description='Average winning trade amount')
    avg_loss: Decimal = Field(description='Average losing trade amount')
    largest_win: Decimal = Field(description='Largest winning trade')
    largest_loss: Decimal = Field(description='Largest losing trade')

class DrawdownAnalysisResponseSchema(BaseModel):
    """Drawdown analysis response schema."""

    strategy_id: UUID = Field(description='Strategy identifier')
    max_drawdown: Decimal = Field(le=0, description='Maximum drawdown percentage')
    max_drawdown_duration: int = Field(ge=0, description='Longest drawdown duration in days')
    current_drawdown: Decimal = Field(le=0, description='Current drawdown')
    drawdown_periods: list[dict[str, Any]] = Field(default_factory=list, description='Historical drawdown periods')


class PortfolioSummaryResponseSchema(BaseModel):
    """Portfolio summary response schema."""

    total_value: Decimal = Field(ge=0, description='Total portfolio value')
    total_pnl: Decimal = Field(description='Total P&L')
    total_return: Decimal = Field(description='Total return percentage')
    active_strategies: int = Field(ge=0, description='Number of active strategies')
    total_trades: int = Field(ge=0, description='Total trades across all strategies')
    win_rate: Decimal = Field(ge=0, le=1, description='Overall win rate')
    sharpe_ratio: Decimal = Field(description='Portfolio Sharpe ratio')


class MarketDataAnalyticsResponseSchema(BaseModel):
    """Market data analytics response schema."""

    instrument: str = Field(description='Trading instrument')
    timeframe: str = Field(description='Data timeframe')
    data_points: list[dict] = Field(default_factory=list, description='OHLCV data points')
    indicators: dict = Field(default_factory=dict, description='Technical indicators')
    last_updated: datetime = Field(description='Last update timestamp')


class BacktestRequestSchema(BaseModel):
    """Request schema for running a backtest."""

    strategy_type: StrategyTypeEnum = Field(description='Type of strategy to backtest')
    parameters: dict = Field(description='Strategy parameters')
    instruments: list[str] = Field(min_length=1, description='Trading instruments')
    start_date: datetime = Field(description='Backtest start date')
    end_date: datetime = Field(description='Backtest end date')
    initial_capital: Decimal = Field(gt=0, description='Starting capital')
    risk_controls: RiskControls = Field(description='Risk management parameters')


class BacktestResults(BaseModel):
    """Response schema for backtest results."""

    backtest_id: str = Field(description='Unique backtest run identifier')
    strategy_type: str = Field(description='Strategy type tested')
    start_date: datetime = Field(description='Backtest period start')
    end_date: datetime = Field(description='Backtest period end')
    initial_capital: Decimal = Field(gt=0, description='Starting capital')
    final_capital: Decimal = Field(gt=0, description='Ending capital')
    total_return: Decimal = Field(description='Total return percentage')
    sharpe_ratio: Decimal = Field(description='Sharpe ratio')
    max_drawdown: Decimal = Field(le=0, description='Maximum drawdown')
    win_rate: Decimal = Field(ge=0, le=1, description='Win rate')
    total_trades: int = Field(ge=0, description='Number of trades executed')
    profit_factor: Decimal = Field(ge=0, description='Profit factor')


class StrategyMetricsComparisonSchema(BaseModel):
    """Comparison of performance metrics across strategies."""

    strategy_id: str = Field(description='Strategy identifier')
    strategy_name: str = Field(description='Strategy name')
    strategy_type: StrategyTypeEnum = Field(description='Strategy type')
    total_return: Decimal = Field(description='Total return percentage')
    annualized_return: Decimal = Field(description='Annualized return percentage')
    sharpe_ratio: Decimal = Field(description='Sharpe ratio')
    max_drawdown: Decimal = Field(description='Maximum drawdown')
    volatility: Decimal = Field(description='Volatility')
    win_rate: Decimal = Field(ge=0, le=1, description='Win rate')
    profit_factor: Decimal = Field(ge=0, description='Profit factor')
    trade_count: int = Field(ge=0, description='Number of trades')


class MetricsComparisonResponseSchema(BaseModel):
    """Response schema for metrics comparison across strategies."""

    period_start: datetime = Field(description='Comparison period start')
    period_end: datetime = Field(description='Comparison period end')
    strategies: list[StrategyMetricsComparisonSchema] = Field(description='Strategy metrics comparison')
    total_strategies: int = Field(ge=0, description='Total number of strategies compared')

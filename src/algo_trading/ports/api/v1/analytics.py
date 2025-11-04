"""
Analytics API endpoints - Hexagonal Architecture Inbound Port.

REST API endpoints for performance analytics, metrics, and backtesting.
Following FastAPI patterns and RFC7807 error handling.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status

from src.algo_trading.adapters.repositories.strategy_repository import StrategyRepository
from src.algo_trading.enums import PeriodEnum
from src.algo_trading.services.performance_analytics import PerformanceAnalytics
from src.algo_trading.services.trade_analytics import TradeAnalytics
from src.algo_trading.services.portfolio_analytics import PortfolioAnalytics
from src.algo_trading.adapters.models.metrics import PerformanceMetricsDocument
from src.algo_trading.ports.api.v1.schemas.analytics_schema import (
    BacktestRequestSchema,
    BacktestResults,
    calculate_period_dates,
    check_period,
    DrawdownAnalysisResponseSchema,
    MarketDataAnalyticsResponseSchema,
    MetricsComparisonResponseSchema,
    PortfolioSummaryResponseSchema,
    StrategyMetricsComparisonSchema,
    TradeAnalyticsResponseSchema,
)

analytics_router = APIRouter(prefix='/api/v1/analytics', tags=['Analytics'])


@analytics_router.get(
    '/strategies/{strategy_id}/metrics/history',
    response_model=list[PerformanceMetricsDocument],
    summary='Get strategy metrics history',
    description='Retrieve historical performance metrics for charting and trend analysis',
)
async def get_metrics_history(
    strategy_id: UUID,
    limit: int = Query(30, ge=1, le=365, description='Number of historical metrics to return'),
) -> list[PerformanceMetricsDocument]:
    """
    Get historical performance metrics for strategy.

    Returns up to `limit` historical metrics snapshots, ordered by newest first.
    Useful for creating performance charts and tracking trends over time.

    Args:
        strategy_id: Unique strategy identifier
        limit: Maximum number of historical records (1-365)

    Returns:
        List of historical PerformanceMetrics (newest first)

    Raises:
        HTTPException 404: Strategy not found
        HTTPException 500: Internal server error
    """
    if not await StrategyRepository.find_by_id(strategy_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategy {strategy_id} not found',
        )

    perf_analytics = PerformanceAnalytics()
    return await perf_analytics.get_metrics_history(strategy_id, limit=limit)


@analytics_router.get(
    '/strategies/{strategy_id}/metrics/latest',
    response_model=PerformanceMetricsDocument,
    summary='Get latest strategy metrics',
    description='Retrieve most recent performance metrics snapshot',
)
async def get_latest_metrics(
    strategy_id: UUID,
) -> PerformanceMetricsDocument:
    """
    Get most recent performance metrics for strategy.

    Returns the latest calculated metrics snapshot from cache.
    Faster than recalculating, useful for dashboards.

    Args:
        strategy_id: Unique strategy identifier

    Returns:
        Latest PerformanceMetrics snapshot

    Raises:
        HTTPException 404: Strategy or metrics not found
        HTTPException 500: Internal server error
    """
    if not await StrategyRepository.find_by_id(strategy_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategy {strategy_id} not found',
        )

    perf_analytics = PerformanceAnalytics()
    metrics = await perf_analytics.get_latest_metrics(strategy_id)

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No metrics found for strategy {strategy_id}',
        )

    return metrics


@analytics_router.get(
    '/strategies/{strategy_id}/performance',
    response_model=PerformanceMetricsDocument,
    summary='Calculate strategy performance metrics',
    description='Calculate (or retrieve cached) performance analytics for a specific trading strategy',
)
async def get_strategy_performance(
    strategy_id: UUID,
    period: PeriodEnum | None = Query(None, description='Time period (1d, 1w, 1m, 3m, 1y, all, custom)'),
    from_date: datetime | None = Query(None, description='Start date for custom period'),
    to_date: datetime | None = Query(None, description='End date for custom period'),
    force_recalculate: bool = Query(False, description='Force recalculation bypassing cache'),
) -> PerformanceMetricsDocument:
    """
    Get strategy performance metrics.

    Args:
        strategy_id: Unique strategy identifier
        period: Time period for analytics calculation
        from_date: Start date for custom period (required if period=custom)
        to_date: End date for custom period (required if period=custom)
        force_recalculate: Skip cache and recalculate metrics

    Returns:
        Performance metrics including returns, Sharpe ratio, drawdown, etc.

    Raises:
        HTTPException 404: Strategy not found
        HTTPException 422: Invalid period parameters
        HTTPException 500: Internal server error
    """
    check_period(from_date, to_date, period)

    from_date, to_date = calculate_period_dates(period)

    if not (strategy := await StrategyRepository.find_by_id(strategy_id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'not found strategy by id={strategy_id}',
        )
    perf_analytics = PerformanceAnalytics()
    return await perf_analytics.calculate_strategy_performance(
        strategy_id=strategy.strategy_id,
        period_start=from_date,
        period_end=to_date,
        force_recalculate=force_recalculate,
    )


@analytics_router.get(
    '/strategies/{strategy_id}/trades',
    response_model=TradeAnalyticsResponseSchema,
    summary='Get strategy trade analytics',
    description='Retrieve detailed trade analytics and statistics for a strategy',
)
async def get_strategy_trades(
    strategy_id: UUID,
    period: PeriodEnum | None = Query(None, description='Time period for analytics'),
    from_date: datetime | None = Query(None, description='Start date for custom period'),
    to_date: datetime | None = Query(None, description='End date for custom period'),
) -> TradeAnalyticsResponseSchema:
    """
    Get strategy trade analytics.

    Args:
        strategy_id: Unique strategy identifier
        period: Time period for analytics calculation
        from_date: Start date for custom period
        to_date: End date for custom period

    Returns:
        Trade analytics with win/loss statistics

    Raises:
        HTTPException 404: Strategy not found
        HTTPException 500: Internal server error
    """
    if not await StrategyRepository.find_by_id(strategy_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategy {strategy_id} not found',
        )

    check_period(from_date, to_date, period)

    period_start, period_end = calculate_period_dates(period)

    trade_analytics = TradeAnalytics()
    return await trade_analytics.calculate_strategy_trades(
        strategy_id=strategy_id,
        period_start=period_start,
        period_end=period_end,
    )


@analytics_router.get(
    '/strategies/{strategy_id}/drawdown',
    response_model=DrawdownAnalysisResponseSchema,
    summary='Get strategy drawdown analysis',
    description='Retrieve drawdown periods and risk analysis for a strategy',
)
async def get_strategy_drawdown(
    strategy_id: UUID,
    period: PeriodEnum | None = Query(None, description='Time period for drawdown analysis'),
    from_date: datetime | None = Query(None, description='Start date for custom period'),
    to_date: datetime | None = Query(None, description='End date for custom period'),
) -> DrawdownAnalysisResponseSchema:
    """
    Get strategy drawdown analysis.

    Args:
        strategy_id: Unique strategy identifier
        period: Time period for analysis
        from_date: Start date for custom period
        to_date: End date for custom period

    Returns:
        Drawdown analysis with historical periods

    Raises:
        HTTPException 404: Strategy not found
        HTTPException 500: Internal server error
    """
    if not await StrategyRepository.find_by_id(strategy_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategy {strategy_id} not found',
        )

    check_period(from_date, to_date, period)
    period_start, period_end = calculate_period_dates(period)

    trade_analytics = TradeAnalytics()
    return await trade_analytics.calculate_strategy_drawdown(
        strategy_id=strategy_id,
        period_start=period_start,
        period_end=period_end,
    )


@analytics_router.get(
    '/portfolio/summary',
    response_model=PortfolioSummaryResponseSchema,
    summary='Get portfolio summary',
    description='Retrieve overall portfolio performance across all strategies',
)
async def get_portfolio_summary(
    period: PeriodEnum | None = Query(None, description='Time period for analytics calculation'),
    from_date: datetime | None = Query(None, description='Start date for custom period'),
    to_date: datetime | None = Query(None, description='End date for custom period'),
) -> PortfolioSummaryResponseSchema:
    """
    Get portfolio summary.

    Aggregates performance metrics across all active/deployed strategies.

    Args:
        period: Time period for analytics
        from_date: Start date for custom period
        to_date: End date for custom period

    Returns:
        Portfolio-wide performance summary

    Raises:
        HTTPException 422: Invalid period parameters
        HTTPException 500: Internal server error
    """
    check_period(from_date, to_date, period)
    period_start, period_end = calculate_period_dates(period)

    portfolio_analytics = PortfolioAnalytics()
    return await portfolio_analytics.calculate_portfolio_summary(
        period_start=period_start,
        period_end=period_end,
    )


@analytics_router.get(
    '/market-data/{instrument}',
    response_model=MarketDataAnalyticsResponseSchema,
    summary='Get market data analytics',
    description='Retrieve market data and technical indicators for an instrument',
)
async def get_market_data(
    instrument: str,
    timeframe: str | None = Query(None, description='Data timeframe (1m, 5m, 15m, 1h, 1d)'),
    limit: int = Query(100, ge=1, le=1000, description='Maximum number of data points to return'),
) -> MarketDataAnalyticsResponseSchema:
    """
    Get market data analytics (T058).

    Args:
        instrument: Trading instrument identifier (ticker/FIGI)
        timeframe: Data timeframe
        limit: Maximum number of data points

    Returns:
        Market data with technical indicators

    Raises:
        HTTPException 404: Instrument not found
        HTTPException 500: Internal server error
    """
    # TODO: Implement actual market data fetching and indicator calculation
    # Mock response
    return MarketDataAnalyticsResponseSchema(
        instrument=instrument,
        timeframe=timeframe or '1d',
        data_points=[
            {'timestamp': '2024-01-01', 'open': 150.0, 'high': 155.0, 'low': 148.0, 'close': 153.0, 'volume': 1000000},
            {'timestamp': '2024-01-02', 'open': 153.0, 'high': 157.0, 'low': 152.0, 'close': 156.0, 'volume': 1200000},
        ],
        indicators={
            'sma_20': 154.5,
            'sma_50': 152.3,
            'rsi_14': 65.2,
            'macd': {'value': 2.1, 'signal': 1.8, 'histogram': 0.3},
        },
        last_updated=datetime.utcnow(),
    )


@analytics_router.post(
    '/backtest',
    response_model=BacktestResults,
    summary='Run strategy backtest',
    description='Run historical backtest for a trading strategy configuration',
)
async def run_backtest(request: BacktestRequestSchema) -> BacktestResults:
    """
    Run strategy backtest (T059).

    Args:
        request: Backtest configuration with strategy parameters and date range

    Returns:
        Backtest results with performance metrics

    Raises:
        HTTPException 400: Invalid backtest parameters
        HTTPException 422: Validation error in request data
        HTTPException 500: Internal server error
    """
    # Validate date range
    if request.end_date <= request.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='end_date must be after start_date')

    # TODO: Implement actual backtest using BacktestEngine service
    # Mock response
    backtest_id = str(uuid4())

    # Calculate mock returns
    total_return = Decimal('0.25')  # 25% return
    final_capital = request.initial_capital * (Decimal('1') + total_return)

    return BacktestResults(
        backtest_id=backtest_id,
        strategy_type=request.strategy_type.value,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        final_capital=final_capital,
        total_return=total_return,
        sharpe_ratio=Decimal('2.1'),
        max_drawdown=Decimal('-0.12'),  # -12%
        win_rate=Decimal('0.68'),  # 68%
        total_trades=150,
        profit_factor=Decimal('3.2'),
    )


@analytics_router.get(
    '/strategies/compare',
    response_model=MetricsComparisonResponseSchema,
    summary='Compare performance metrics across strategies',
    description='Compare latest performance metrics across multiple strategies for the same period',
)
async def compare_strategies(
    strategy_ids: list[UUID] = Query(..., description='List of strategy IDs to compare (2-10)'),
    period: PeriodEnum | None = Query(None, description='Time period for comparison'),
    from_date: datetime | None = Query(None, description='Start date for custom period'),
    to_date: datetime | None = Query(None, description='End date for custom period'),
) -> MetricsComparisonResponseSchema:
    """
    Compare performance metrics across multiple strategies.

    Retrieves latest metrics for each strategy in the specified period and returns
    a comparison view. Useful for portfolio analysis and strategy selection.

    Args:
        strategy_ids: List of 2-10 strategy UUIDs to compare
        period: Time period for comparison (defaults to last 30 days)
        from_date: Start date for custom period
        to_date: End date for custom period

    Returns:
        Comparison of metrics across all strategies

    Raises:
        HTTPException 400: Invalid number of strategies (must be 2-10)
        HTTPException 404: One or more strategies not found
        HTTPException 422: Invalid period parameters
        HTTPException 500: Internal server error
    """
    min_strategies = 2
    max_strategies = 10
    if not (min_strategies <= len(strategy_ids) <= max_strategies):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Must provide between 2 and 10 strategies to compare',
        )

    if period == PeriodEnum.custom and (from_date is None or to_date is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='from_date and to_date are required when period=custom',
        )

    if period:
        from_date, to_date = calculate_period_dates(period)
    elif from_date is None or to_date is None:
        from_date, to_date = calculate_period_dates(PeriodEnum.month)

    strategies = await StrategyRepository.find_by_ids(strategy_ids)
    found_strategy_ids = {s.strategy_id for s in strategies}
    missing_ids = set(strategy_ids) - found_strategy_ids

    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategies not found: {", ".join(str(sid) for sid in missing_ids)}',
        )

    perf_analytics = PerformanceAnalytics()
    comparison_data = []

    for strategy in strategies:
        try:
            metrics = await perf_analytics.calculate_strategy_performance(
                strategy_id=strategy.strategy_id,
                period_start=from_date,
                period_end=to_date,
                cache_ttl_hours=1,
                force_recalculate=False,
            )

            comparison_data.append(
                StrategyMetricsComparisonSchema(
                    strategy_id=str(strategy.strategy_id),
                    strategy_name=strategy.name,
                    strategy_type=strategy.strategy_type,
                    total_return=metrics.total_return,
                    annualized_return=metrics.annualized_return,
                    sharpe_ratio=metrics.sharpe_ratio,
                    max_drawdown=metrics.max_drawdown,
                    volatility=metrics.volatility,
                    win_rate=metrics.win_rate,
                    profit_factor=metrics.profit_factor,
                    trade_count=metrics.trade_count,
                ),
            )
        except Exception as e:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to calculate metrics for strategy {strategy.strategy_id}: {e!s}',
            ) from e

    return MetricsComparisonResponseSchema(
        period_start=from_date,
        period_end=to_date,
        strategies=comparison_data,
        total_strategies=len(comparison_data),
    )

"""PerformanceAnalytics Service - Application Use Case Layer.

Orchestrates performance metrics calculation and storage.
"""

from datetime import datetime, timedelta, UTC
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.algo_trading.adapters.models import (
    OrderSideEnum,
    OrderStatusEnum,
    PerformanceMetricsDocument,
    TradeOrderDocument,
    TradingSessionDocument,
)
from src.algo_trading.domain.analytics.performance_calculator import PerformanceCalculator, Trade


class PerformanceAnalyticsError(Exception):
    """Performance analytics operation failed."""


class PerformanceAnalytics:
    """
    Application service for performance metrics calculation.

    Orchestrates domain logic for analytics and persists results.
    """

    def __init__(
        self,
        calculator: PerformanceCalculator | None = None
    ) -> None:
        """
        Initialize PerformanceAnalytics.

        Args:
            calculator: Domain calculator for performance metrics
        """
        self.calculator = calculator or PerformanceCalculator()

    async def calculate_strategy_performance(
        self,
        strategy_id: UUID,
        period_start: datetime,
        period_end: datetime,
        cache_ttl_hours: int = 1,
        force_recalculate: bool = False,
    ) -> PerformanceMetricsDocument:
        """
        Calculate and store performance metrics for strategy with smart caching.

        Metrics are cached to avoid expensive recalculations. Use cache_ttl_hours to control
        how long cached metrics are considered fresh. Set force_recalculate=True to bypass cache.

        Args:
            strategy_id: Strategy UUID
            period_start: Analysis period start
            period_end: Analysis period end
            cache_ttl_hours: Cache time-to-live in hours (default: 1 hour)
            force_recalculate: If True, bypass cache and recalculate (default: False)

        Returns:
            Calculated PerformanceMetrics (from cache or freshly calculated)

        Raises:
            PerformanceAnalyticsError: If calculation fails
        """
        if period_end <= period_start:
            raise PerformanceAnalyticsError('period_end must be after period_start')

        if not force_recalculate:
            cache_threshold = datetime.now() - timedelta(hours=cache_ttl_hours)

            cached_metrics = await PerformanceMetricsDocument.find_one(
                PerformanceMetricsDocument.strategy_id == strategy_id,
                PerformanceMetricsDocument.period_start == period_start,
                PerformanceMetricsDocument.period_end == period_end,
                PerformanceMetricsDocument.calculated_at >= cache_threshold,
            )

            if cached_metrics:
                return cached_metrics

        sessions = await TradingSessionDocument.find(
            TradingSessionDocument.strategy_id == strategy_id,
            TradingSessionDocument.session_start >= period_start,
            TradingSessionDocument.session_start <= period_end,
        ).to_list()

        if not sessions:
            raise PerformanceAnalyticsError(f'No trading sessions found for strategy {strategy_id} in period')

        starting_capital = sessions[0].starting_capital
        ending_capital = sessions[-1].ending_capital or sessions[-1].starting_capital

        orders = await TradeOrderDocument.find(
            TradeOrderDocument.strategy_id == strategy_id,
            TradeOrderDocument.filled_at != None,
            TradeOrderDocument.filled_at >= period_start,  # type: ignore[operator]
            TradeOrderDocument.filled_at <= period_end,  # type: ignore[operator]
            TradeOrderDocument.status == OrderStatusEnum.FILLED,
        ).to_list()

        if not orders:
            raise PerformanceAnalyticsError('No filled orders found in period')

        equity_curve, daily_returns = await self._build_equity_curve(orders, starting_capital)

        trades = await self._build_trade_list(orders)

        days = (period_end - period_start).days

        perf_result = self.calculator.calculate_performance(
            starting_capital=starting_capital,
            ending_capital=ending_capital,
            returns=daily_returns,
            equity_curve=equity_curve,
            trades=trades,
            days=days,
        )

        metrics = PerformanceMetricsDocument(
            strategy_id=strategy_id,
            period_start=period_start,
            period_end=period_end,
            total_return=perf_result.total_return,
            annualized_return=perf_result.annualized_return,
            sharpe_ratio=perf_result.sharpe_ratio,
            max_drawdown=perf_result.max_drawdown,
            volatility=perf_result.volatility,
            win_rate=perf_result.win_rate,
            profit_factor=perf_result.profit_factor,
            trade_count=perf_result.trade_count,
            average_win=perf_result.average_win,
            average_loss=perf_result.average_loss,
            largest_win=perf_result.largest_win,
            largest_loss=perf_result.largest_loss,
        )

        await metrics.insert()

        return metrics

    async def get_latest_metrics(self, strategy_id: UUID) -> PerformanceMetricsDocument | None:
        """
        Get most recent performance metrics for strategy.

        Args:
            strategy_id: Strategy UUID

        Returns:
            Latest PerformanceMetrics or None
        """
        metrics = (
            await PerformanceMetricsDocument.find(PerformanceMetricsDocument.strategy_id == strategy_id)
            .sort('-period_end')
            .limit(1)
            .to_list()
        )

        return metrics[0] if metrics else None

    async def get_metrics_history(self, strategy_id: UUID, limit: int = 30) -> list[PerformanceMetricsDocument]:
        """
        Get performance metrics history for strategy.

        Args:
            strategy_id: Strategy UUID
            limit: Max results

        Returns:
            List of PerformanceMetrics (newest first)
        """
        return (
            await PerformanceMetricsDocument.find(PerformanceMetricsDocument.strategy_id == strategy_id)
            .sort('-period_end')
            .limit(limit)
            .to_list()
        )

    async def calculate_trailing_metrics(self, strategy_id: UUID, days: int = 30) -> PerformanceMetricsDocument:
        """
        Calculate trailing N-day performance metrics.

        Args:
            strategy_id: Strategy UUID
            days: Trailing period in days

        Returns:
            PerformanceMetrics for trailing period
        """
        period_end = datetime.now(tz=UTC)
        period_start = period_end - timedelta(days=days)

        return await self.calculate_strategy_performance(
            strategy_id=strategy_id,
            period_start=period_start,
            period_end=period_end,
        )

    @classmethod
    def get_daily_return(cls, daily_pnl: Decimal, current_capital: Decimal) -> Decimal:
        return daily_pnl / (current_capital - daily_pnl) if (current_capital - daily_pnl) > 0 else Decimal('0')

    async def _build_equity_curve(
        self,
        orders: list[TradeOrderDocument],
        starting_capital: Decimal,
    ) -> tuple[list[Decimal], list[Decimal]]:
        """
        Build equity curve and daily returns from orders.

        Args:
            orders: List of filled orders
            starting_capital: Starting capital

        Returns:
            Tuple of (equity_curve, daily_returns)
        """
        equity_curve = [starting_capital]
        daily_returns = []

        current_capital = starting_capital

        orders_by_day: dict[str, list[TradeOrderDocument]] = {}
        sorted_order = sorted(
            [o for o in orders if o.filled_at is not None],
            key=lambda o: o.filled_at if o.filled_at else datetime.min,
        )
        for order in sorted_order:
            if order.filled_at is None:
                continue
            day_key = order.filled_at.date().isoformat()
            if day_key not in orders_by_day:
                orders_by_day[day_key] = []
            orders_by_day[day_key].append(order)

        for day_orders in orders_by_day.values():
            daily_pnl = Decimal('0')

            for order in day_orders:
                # Simplified P&L calculation
                # Real implementation would track position-level P&L
                if order.filled_price is None:
                    continue
                order_value = order.filled_price * order.filled_quantity
                daily_pnl += order_value if order.side == OrderSideEnum.SELL else -order_value
                daily_pnl -= order.commission

            current_capital += daily_pnl
            equity_curve.append(current_capital)

            daily_return = self.get_daily_return(daily_pnl, current_capital)
            daily_returns.append(daily_return)

        return equity_curve, daily_returns

    async def _build_trade_list(self, orders: list[TradeOrderDocument]) -> list[Trade]:
        """
        Build trade list from orders for performance calculation.

        Args:
            orders: List of filled orders

        Returns:
            List of Trade domain objects
        """
        trades = []

        # Group buy/sell pairs (simplified)
        # Real implementation would match specific positions
        for _order in orders:
            # Calculate P&L (simplified)
            pnl = Decimal('0')  # Would calculate from matched positions
            return_pct = Decimal('0')  # Would calculate from matched positions

            trade = Trade(pnl=pnl, return_pct=return_pct)
            trades.append(trade)

        return trades

    async def calculate_trade_analytics(
        self,
        strategy_id: UUID,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> dict:
        """
        Calculate trade-level analytics for strategy.

        Args:
            strategy_id: Strategy UUID
            period_start: Optional period start
            period_end: Optional period end

        Returns:
            Dictionary with trade analytics
        """
        query: dict[str, Any] = {'strategy_id': strategy_id, 'status': OrderStatusEnum.FILLED}

        if period_start:
            query['filled_at'] = {'$gte': period_start}

        if period_end:
            if 'filled_at' in query:
                filled_at_query = query['filled_at']
                if isinstance(filled_at_query, dict):
                    filled_at_query['$lte'] = period_end
            else:
                query['filled_at'] = {'$lte': period_end}

        orders = await TradeOrderDocument.find(query).to_list()

        if not orders:
            return {
                'total_trades': 0,
                'total_volume': Decimal('0'),
                'total_commission': Decimal('0'),
                'average_fill_price': Decimal('0'),
            }

        total_trades = len(orders)
        total_volume = sum(o.filled_quantity for o in orders)
        total_commission = sum(o.commission for o in orders)
        filled_prices = [o.filled_price for o in orders if o.filled_price is not None]
        average_fill_price = Decimal('0')
        if filled_prices:
            average_fill_price = sum(filled_prices, Decimal('0')) / len(filled_prices)

        return {
            'total_trades': total_trades,
            'total_volume': total_volume,
            'total_commission': total_commission,
            'average_fill_price': average_fill_price,
            'orders': orders,
        }

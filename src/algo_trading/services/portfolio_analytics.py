"""Portfolio Analytics Service - Application Use Case Layer.

Orchestrates portfolio-level analytics across multiple strategies.
"""

from decimal import Decimal
from datetime import datetime

from algo_trading.enums import OrderSideEnum
from src.algo_trading.adapters.models import (
    TradingStrategyDocument,
    StrategyStatusEnum,
    TradeOrderDocument,
    OrderStatusEnum,
)
from src.algo_trading.ports.api.v1.schemas.analytics_schema import PortfolioSummaryResponseSchema


class PortfolioAnalytics:
    """
    Application service for portfolio-level analytics.

    Aggregates performance metrics across all active strategies.
    """

    @staticmethod
    async def calculate_portfolio_summary(
        period_start: datetime,
        period_end: datetime,
    ) -> PortfolioSummaryResponseSchema:
        """
        Calculate portfolio-wide performance summary.

        Aggregates metrics from all active/deployed strategies in the period.

        Args:
            period_start: Analysis period start
            period_end: Analysis period end

        Returns:
            PortfolioSummaryResponseSchema with aggregated metrics
        """
        strategies = await TradingStrategyDocument.find(
            TradingStrategyDocument.status == StrategyStatusEnum.ACTIVE,
        ).to_list()

        if not strategies:
            return PortfolioSummaryResponseSchema(
                total_value=Decimal('0'),
                total_pnl=Decimal('0'),
                total_return=Decimal('0'),
                active_strategies=0,
                total_trades=0,
                win_rate=Decimal('0'),
                sharpe_ratio=Decimal('0'),
            )

        strategy_ids = [s.strategy_id for s in strategies]

        orders = await TradeOrderDocument.find(
            TradeOrderDocument.strategy_id.in_(strategy_ids),  # type: ignore[attr-defined]
            TradeOrderDocument.status == OrderStatusEnum.FILLED,
            TradeOrderDocument.filled_at != None,  # noqa: E711
            TradeOrderDocument.filled_at >= period_start,  # type: ignore[operator]
            TradeOrderDocument.filled_at <= period_end,  # type: ignore[operator]
        ).to_list()

        total_trades = len(orders)
        total_pnl = Decimal('0')
        winning_trades = 0
        losing_trades = 0

        for order in orders:
            if order.side == OrderSideEnum.SELL and order.filled_price and order.filled_quantity:
                pnl = (order.filled_price * order.filled_quantity) - order.commission
            elif order.side == OrderSideEnum.BUY and order.filled_price and order.filled_quantity:
                pnl = -(order.filled_price * order.filled_quantity) - order.commission
            else:
                pnl = Decimal('0')

            total_pnl += pnl

            if pnl > 0:
                winning_trades += 1
            elif pnl < 0:
                losing_trades += 1

        win_rate = Decimal('0')
        max_traders = 10
        if total_trades > 0:
            win_rate = Decimal(str(winning_trades)) / Decimal(str(total_trades))

        total_value = Decimal('100000') + total_pnl
        total_return = total_pnl / Decimal('100000') if total_value > 0 else Decimal('0')

        sharpe_ratio = Decimal('0')
        if total_trades > max_traders and total_return > 0:
            sharpe_ratio = total_return * Decimal('2')

        return PortfolioSummaryResponseSchema(
            total_value=total_value,
            total_pnl=total_pnl,
            total_return=total_return,
            active_strategies=len(strategies),
            total_trades=total_trades,
            win_rate=win_rate,
            sharpe_ratio=sharpe_ratio,
        )

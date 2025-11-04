from decimal import Decimal
from uuid import UUID
from datetime import datetime

from src.algo_trading.ports.api.v1.schemas.analytics_schema import (
    TradeAnalyticsResponseSchema,
    DrawdownAnalysisResponseSchema,
)
from src.algo_trading.adapters.models import TradeOrderDocument, OrderStatusEnum, OrderSideEnum


class TradeAnalytics:
    """
    Application service for trade analytics calculation.

    Orchestrates trade data retrieval and statistics calculation.
    """

    @staticmethod
    async def calculate_strategy_trades(
        strategy_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> TradeAnalyticsResponseSchema:
        """
        Calculate trade analytics for strategy within period.

        Args:
            strategy_id: Strategy UUID
            period_start: Analysis period start
            period_end: Analysis period end

        Returns:
            TradeAnalyticsResponseSchema
        """
        orders = await TradeOrderDocument.find(
            TradeOrderDocument.strategy_id == strategy_id,
            TradeOrderDocument.status == OrderStatusEnum.FILLED,
            TradeOrderDocument.filled_at != None,  # noqa: E711
            TradeOrderDocument.filled_at >= period_start,  # type: ignore[operator]
            TradeOrderDocument.filled_at <= period_end,  # type: ignore[operator]
        ).to_list()

        if not orders:
            return TradeAnalyticsResponseSchema(
                strategy_id=strategy_id,
                period_start=period_start,
                period_end=period_end,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                avg_win=Decimal('0'),
                avg_loss=Decimal('0'),
                largest_win=Decimal('0'),
                largest_loss=Decimal('0'),
            )
        trades_with_pnl = []
        for order in orders:
            if order.side == OrderSideEnum.SELL and order.filled_price and order.filled_quantity:
                pnl = (order.filled_price * order.filled_quantity) - order.commission
            elif order.side == OrderSideEnum.BUY and order.filled_price and order.filled_quantity:
                pnl = -(order.filled_price * order.filled_quantity) - order.commission
            else:
                pnl = Decimal('0')

            trades_with_pnl.append(pnl)

        calculates = TradeMetricsCalculator.calculate_trade_analytics(trades_with_pnl)
        return TradeAnalyticsResponseSchema(
            strategy_id=strategy_id,
            period_start=period_start,
            period_end=period_end,
            total_trades=calculates['total_trades'],
            winning_trades=calculates['winning_trades'],
            losing_trades=calculates['losing_trades'],
            avg_win=calculates['avg_win'],
            avg_loss=calculates['avg_loss'],
            largest_win=calculates['largest_win'],
            largest_loss=calculates['largest_loss'],
        )

    @staticmethod
    async def calculate_strategy_drawdown(
        strategy_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> DrawdownAnalysisResponseSchema:
        """
        Calculate drawdown analysis for strategy within period.

        Args:
            strategy_id: Strategy UUID
            period_start: Analysis period start
            period_end: Analysis period end

        Returns:
            DrawdownAnalysisResponseSchema with drawdown metrics
        """
        orders = await TradeOrderDocument.find(
            TradeOrderDocument.strategy_id == strategy_id,
            TradeOrderDocument.status == OrderStatusEnum.FILLED,
            TradeOrderDocument.filled_at != None,  # noqa: E711
            TradeOrderDocument.filled_at >= period_start,  # type: ignore[operator]
            TradeOrderDocument.filled_at <= period_end,  # type: ignore[operator]
        ).sort('filled_at').to_list()

        if not orders:
            return DrawdownAnalysisResponseSchema(
                strategy_id=strategy_id,
                max_drawdown=Decimal('0'),
                max_drawdown_duration=0,
                current_drawdown=Decimal('0'),
                drawdown_periods=[],
            )

        equity_curve = []
        running_capital = Decimal('100000')

        for order in orders:
            if order.side == OrderSideEnum.SELL and order.filled_price and order.filled_quantity:
                pnl = (order.filled_price * order.filled_quantity) - order.commission
            elif order.side == OrderSideEnum.BUY and order.filled_price and order.filled_quantity:
                pnl = -(order.filled_price * order.filled_quantity) - order.commission
            else:
                pnl = Decimal('0')

            running_capital += pnl
            equity_curve.append({
                'timestamp': order.filled_at,
                'equity': running_capital,
            })

        drawdown_result = TradeMetricsCalculator.calculate_drawdown_analysis(equity_curve)

        return DrawdownAnalysisResponseSchema(
            strategy_id=strategy_id,
            max_drawdown=drawdown_result['max_drawdown'],
            max_drawdown_duration=drawdown_result['max_drawdown_duration'],
            current_drawdown=drawdown_result['current_drawdown'],
            drawdown_periods=drawdown_result['drawdown_periods'],
        )


class TradeMetricsCalculator:
    """Domain calculator for trade metrics - pure mathematical functions."""

    @staticmethod
    def calculate_trade_analytics(trades: list[Decimal]) -> dict:
        """Calculate analytics from a list of trades."""
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "avg_win": Decimal("0"),
                "avg_loss": Decimal("0"),
                "largest_win": Decimal("0"),
                "largest_loss": Decimal("0"),
            }

        winning_trades = []
        losing_trades = []

        for trade in trades:
            pnl = (
                getattr(trade, "pnl", None)
                or getattr(trade, "profit_loss", None)
                or Decimal("0")
            )

            if pnl > 0:
                winning_trades.append(pnl)
            elif pnl < 0:
                losing_trades.append(pnl)

        total_trades = len(trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)

        avg_win = Decimal("0")
        if winning_trades:
            avg_win = sum(winning_trades) / Decimal(str(winning_count))

        avg_loss = Decimal("0")
        if losing_trades:
            avg_loss = sum(losing_trades) / Decimal(str(losing_count))

        largest_win = max(winning_trades) if winning_trades else Decimal("0")
        largest_loss = min(losing_trades) if losing_trades else Decimal("0")

        return {
            "total_trades": total_trades,
            "winning_trades": winning_count,
            "losing_trades": losing_count,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
        }

    @staticmethod
    def calculate_drawdown_analysis(equity_curve: list[dict]) -> dict:
        """
        Calculate comprehensive drawdown analysis from equity curve.

        Args:
            equity_curve: List of dicts with 'timestamp' and 'equity' keys

        Returns:
            Dictionary with drawdown metrics:
                - max_drawdown: Maximum drawdown percentage
                - max_drawdown_duration: Duration in days
                - current_drawdown: Current drawdown percentage
                - drawdown_periods: List of drawdown periods
        """
        if not equity_curve:
            return {
                'max_drawdown': Decimal('0'),
                'max_drawdown_duration': 0,
                'current_drawdown': Decimal('0'),
                'drawdown_periods': [],
            }

        peak = equity_curve[0]['equity']
        max_drawdown = Decimal('0')
        max_drawdown_duration = 0
        current_drawdown = Decimal('0')
        drawdown_periods = []

        in_drawdown = False
        drawdown_start = None
        drawdown_start_equity = None

        for i, point in enumerate(equity_curve):
            equity = point['equity']
            timestamp = point['timestamp']

            if equity > peak:
                if in_drawdown and drawdown_start:
                    drawdown_pct = (drawdown_start_equity - peak) / peak if peak > 0 else Decimal('0')
                    drawdown_periods.append({
                        'start': drawdown_start.isoformat(),
                        'end': timestamp.isoformat(),
                        'drawdown': float(drawdown_pct),
                    })
                    in_drawdown = False

                peak = equity

            drawdown = (equity - peak) / peak if peak > 0 else Decimal('0')

            if drawdown < 0 and not in_drawdown:
                in_drawdown = True
                drawdown_start = timestamp
                drawdown_start_equity = peak

            if drawdown < max_drawdown:
                max_drawdown = drawdown
                if drawdown_start:
                    max_drawdown_duration = (timestamp - drawdown_start).days

            if i == len(equity_curve) - 1:
                current_drawdown = drawdown

        if in_drawdown and drawdown_start:
            last_point = equity_curve[-1]
            drawdown_pct = (last_point['equity'] - peak) / peak if peak > 0 else Decimal('0')
            drawdown_periods.append({
                'start': drawdown_start.isoformat(),
                'end': last_point['timestamp'].isoformat(),
                'drawdown': float(drawdown_pct),
            })

        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_duration,
            'current_drawdown': current_drawdown,
            'drawdown_periods': drawdown_periods,
        }


class AdvancedTradeMetricsCalculator:
    """Domain calculator for advanced trade metrics - optional calculations."""

    @staticmethod
    def calculate_win_rate(winning_trades: int, total_trades: int) -> Decimal:
        """Calculate win rate percentage."""
        if total_trades == 0:
            return Decimal("0")
        return (Decimal(str(winning_trades)) / Decimal(str(total_trades))) * Decimal(
            "100",
        )

    @staticmethod
    def calculate_profit_factor(
        winning_trades: list[Decimal],
        losing_trades: list[Decimal],
    ) -> Decimal:
        """Calculate profit factor (gross profit / gross loss)."""
        gross_profit = Decimal(str(sum(winning_trades))) if winning_trades else Decimal("0")
        gross_loss = Decimal(str(abs(sum(losing_trades)))) if losing_trades else Decimal("0")

        if gross_loss == 0:
            return (
                Decimal("0") if gross_profit == 0 else Decimal("999.99")
            )

        return gross_profit / Decimal(gross_loss)

    @staticmethod
    def calculate_max_drawdown(trades: list) -> Decimal:
        """Calculate maximum drawdown from a series of trades."""
        if not trades:
            return Decimal("0")

        sorted_trades = sorted(trades, key=lambda x: x.created_at)
        running_pnl = Decimal("0")
        peak = Decimal("0")
        max_drawdown = Decimal("0")

        for trade in sorted_trades:
            pnl = (
                getattr(trade, "pnl", None)
                or getattr(trade, "profit_loss", None)
                or Decimal("0")
            )
            running_pnl += pnl

            peak = max(peak, running_pnl)

            drawdown = peak - running_pnl
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

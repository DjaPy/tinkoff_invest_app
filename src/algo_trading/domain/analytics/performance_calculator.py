"""Performance Calculation Domain Logic - Hexagonal Architecture Domain Layer.

Pure business logic for performance metrics, independent of infrastructure.
"""

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import NamedTuple, Sequence


class TradeStatistic(NamedTuple):
    win_rate: Decimal
    profit_factor: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal


@dataclass(frozen=True)
class Trade:
    """Individual trade data for performance calculation."""

    pnl: Decimal  # Profit or loss
    return_pct: Decimal  # Return as percentage


@dataclass(frozen=True)
class PerformanceResult:
    """Calculated performance metrics."""

    total_return: Decimal
    annualized_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    volatility: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    trade_count: int
    average_win: Decimal
    average_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal


class PerformanceCalculator:
    """
    Pure domain logic for performance metrics calculation.

    No infrastructure dependencies - only operates on domain objects.
    """

    TRADING_DAYS_PER_YEAR = 252
    RISK_FREE_RATE = Decimal("0.03")  # 3% annual risk-free rate

    @staticmethod
    def calculate_total_return(
        starting_capital: Decimal,
        ending_capital: Decimal,
    ) -> Decimal:
        """
        Calculate total return percentage.

        Args:
            starting_capital: Initial capital
            ending_capital: Final capital

        Returns:
            Total return as decimal (0.15 = 15%)
        """
        if starting_capital == 0:
            return Decimal("0")

        return (ending_capital - starting_capital) / starting_capital

    @staticmethod
    def calculate_annualized_return(
        total_return: Decimal,
        days: int,
    ) -> Decimal:
        """
        Calculate annualized return from total return.

        Args:
            total_return: Total return as decimal
            days: Number of trading days

        Returns:
            Annualized return as decimal
        """
        if days == 0:
            return Decimal("0")

        # Compound annual growth rate (CAGR)
        years = Decimal(days) / Decimal(PerformanceCalculator.TRADING_DAYS_PER_YEAR)
        if years == 0:
            return total_return

        # (1 + return)^(1/years) - 1
        return_factor = float(1 + total_return)
        annualized = Decimal(math.pow(return_factor, 1 / float(years)) - 1)

        return annualized

    @staticmethod
    def calculate_volatility(returns: list[Decimal]) -> Decimal:
        """
        Calculate return volatility (standard deviation).

        Args:
            returns: List of periodic returns

        Returns:
            Volatility as decimal
        """
        if len(returns) < 2:
            return Decimal("0")

        # Calculate mean
        mean_return = Decimal(sum(returns)) / Decimal(len(returns))

        # Calculate variance
        variance = Decimal(sum((r - mean_return) ** 2 for r in returns)) / (Decimal(len(returns) - 1))

        # Standard deviation
        volatility = Decimal(math.sqrt(float(variance)))

        return volatility

    @staticmethod
    def calculate_sharpe_ratio(
        average_return: Decimal,
        volatility: Decimal,
        risk_free_rate: Decimal | None = None,
    ) -> Decimal:
        """
        Calculate Sharpe ratio (risk-adjusted return).

        Args:
            average_return: Average periodic return
            volatility: Return volatility
            risk_free_rate: Risk-free rate (defaults to 3% annual)

        Returns:
            Sharpe ratio
        """
        if volatility == 0:
            return Decimal("0")

        if risk_free_rate is None:
            risk_free_rate = PerformanceCalculator.RISK_FREE_RATE

        # Adjust risk-free rate to periodic rate (assuming daily)
        periodic_rf = risk_free_rate / Decimal(PerformanceCalculator.TRADING_DAYS_PER_YEAR)

        excess_return = average_return - periodic_rf
        sharpe = excess_return / volatility

        # Annualize
        sharpe_annualized = sharpe * Decimal(math.sqrt(PerformanceCalculator.TRADING_DAYS_PER_YEAR))

        return sharpe_annualized

    @staticmethod
    def calculate_max_drawdown(equity_curve: Sequence[Decimal]) -> Decimal:
        """
        Calculate maximum drawdown from equity curve.

        Args:
            equity_curve: Sequence of portfolio values over time

        Returns:
            Maximum drawdown as negative decimal (-0.15 = -15%)
        """
        if len(equity_curve) < 2:
            return Decimal("0")

        max_drawdown = Decimal("0")
        peak = equity_curve[0]

        for value in equity_curve:
            if value > peak:
                peak = value

            drawdown = (value - peak) / peak if peak > 0 else Decimal("0")
            max_drawdown = min(max_drawdown, drawdown)

        return max_drawdown

    @staticmethod
    def calculate_trade_statistics(
            trades: list[Trade]
    ) -> TradeStatistic:
        """
        Calculate trade-level statistics.

        Args:
            trades: Sequence of completed trades

        Returns:
            Tuple of (win_rate, profit_factor, avg_win, avg_loss, largest_win, largest_loss)
        """
        if not trades:
            return TradeStatistic(Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"))

        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]

        # Win rate
        win_rate = Decimal(len(winning_trades)) / Decimal(len(trades))

        # Profit factor
        gross_profit = Decimal(sum((t.pnl for t in winning_trades), Decimal("0"))) if winning_trades else Decimal("0")
        gross_loss = Decimal(abs(sum((t.pnl for t in losing_trades), Decimal("0")))) if losing_trades else Decimal("0")
        profit_factor = gross_profit / gross_loss if gross_loss > Decimal("0") else Decimal("0")

        # Average win/loss
        avg_win = gross_profit / len(winning_trades) if winning_trades else Decimal("0")
        avg_loss = gross_loss / len(losing_trades) if losing_trades else Decimal("0")

        # Largest win/loss
        largest_win = max((t.pnl for t in winning_trades), default=Decimal("0"))
        largest_loss = min((t.pnl for t in losing_trades), default=Decimal("0"))

        return TradeStatistic(win_rate, profit_factor, avg_win, avg_loss, largest_win, largest_loss)

    @staticmethod
    def calculate_performance(
        starting_capital: Decimal,
        ending_capital: Decimal,
        returns: list[Decimal],
        equity_curve: list[Decimal],
        trades: list[Trade],
        days: int,
    ) -> PerformanceResult:
        """
        Calculate comprehensive performance metrics.

        Args:
            starting_capital: Initial capital
            ending_capital: Final capital
            returns: Daily/periodic returns
            equity_curve: Portfolio value over time
            trades: Completed trades
            days: Number of trading days

        Returns:
            PerformanceResult with all metrics
        """
        total_return = PerformanceCalculator.calculate_total_return(
            starting_capital, ending_capital
        )

        annualized_return = PerformanceCalculator.calculate_annualized_return(
            total_return, days
        )

        volatility = PerformanceCalculator.calculate_volatility(returns)
        pre_average_return = Decimal(sum((r for r in returns), Decimal("0"))) / Decimal(len(returns))
        average_return = pre_average_return if returns else Decimal("0")
        sharpe_ratio = PerformanceCalculator.calculate_sharpe_ratio(
            average_return, volatility
        )

        max_drawdown = PerformanceCalculator.calculate_max_drawdown(equity_curve)

        trade_statistics = (
            PerformanceCalculator.calculate_trade_statistics(trades)
        )

        return PerformanceResult(
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            volatility=volatility,
            win_rate=trade_statistics.win_rate,
            profit_factor=trade_statistics.profit_factor,
            trade_count=len(trades),
            average_win=trade_statistics.avg_win,
            average_loss=trade_statistics.avg_loss,
            largest_win=trade_statistics.largest_win,
            largest_loss=trade_statistics.largest_loss,
        )

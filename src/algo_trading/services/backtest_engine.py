"""BacktestEngine Service - Application Use Case Layer.

Orchestrates backtesting strategies against historical data.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from ..adapters.models.market_data import MarketData
from ..domain.analytics.performance_calculator import (PerformanceCalculator,
                                                       PerformanceResult,
                                                       Trade)


@dataclass
class BacktestConfig:
    """Backtesting configuration."""

    strategy_type: str
    parameters: dict
    instruments: list[str]
    period_start: datetime
    period_end: datetime
    starting_capital: Decimal
    commission_rate: Decimal = Decimal("0.001")  # 0.1% per trade


@dataclass
class BacktestResult:
    """Backtesting result."""

    config: BacktestConfig
    performance: PerformanceResult
    trades: list[dict[str, Any]]
    equity_curve: list[Decimal]
    execution_time_ms: float


class BacktestEngineError(Exception):
    """Backtesting operation failed."""

    pass


class BacktestEngine:
    """
    Application service for strategy backtesting.

    Simulates strategy execution on historical data.
    """

    def __init__(self, calculator: Optional[PerformanceCalculator] = None):
        """
        Initialize BacktestEngine.

        Args:
            calculator: Domain calculator for performance metrics
        """
        self.calculator = calculator or PerformanceCalculator()

    async def run_backtest(
        self,
        config: BacktestConfig,
    ) -> BacktestResult:
        """
        Run backtest for strategy configuration.

        Args:
            config: Backtesting configuration

        Returns:
            BacktestResult with performance metrics

        Raises:
            BacktestEngineError: If backtest fails
        """
        start_time = datetime.utcnow()

        # Load historical market data
        market_data = await self._load_market_data(
            instruments=config.instruments,
            period_start=config.period_start,
            period_end=config.period_end,
        )

        if not market_data:
            raise BacktestEngineError("No market data found for backtest period")

        # Simulate strategy execution
        trades, equity_curve = await self._simulate_strategy(config, market_data)

        # Calculate performance metrics
        trade_objs = [
            Trade(
                pnl=t["pnl"],
                return_pct=t["return_pct"],
            )
            for t in trades
        ]

        daily_returns = self._calculate_daily_returns(equity_curve)

        days = (config.period_end - config.period_start).days

        performance = self.calculator.calculate_performance(
            starting_capital=config.starting_capital,
            ending_capital=equity_curve[-1] if equity_curve else config.starting_capital,
            returns=daily_returns,
            equity_curve=equity_curve,
            trades=trade_objs,
            days=days,
        )

        end_time = datetime.utcnow()
        execution_time_ms = (end_time - start_time).total_seconds() * 1000

        return BacktestResult(
            config=config,
            performance=performance,
            trades=trades,
            equity_curve=equity_curve,
            execution_time_ms=execution_time_ms,
        )

    async def _load_market_data(
        self,
        instruments: list[str],
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, list[MarketData]]:
        """
        Load historical market data for instruments.

        Args:
            instruments: List of trading instruments
            period_start: Period start
            period_end: Period end

        Returns:
            Dictionary mapping instrument to sorted market data
        """
        data_by_instrument = {}

        for instrument in instruments:
            market_data = await MarketData.find(
                MarketData.instrument == instrument,
                MarketData.timestamp >= period_start,
                MarketData.timestamp <= period_end,
            ).sort("timestamp").to_list()

            data_by_instrument[instrument] = market_data

        return data_by_instrument

    async def _simulate_strategy(
        self,
        config: BacktestConfig,
        market_data: dict[str, list[MarketData]],
    ) -> tuple[list[dict], list[Decimal]]:
        """
        Simulate strategy execution on historical data.

        Args:
            config: Backtest configuration
            market_data: Historical market data

        Returns:
            Tuple of (trades, equity_curve)

        Note:
            This is a simplified simulation. Real implementation would:
            - Implement specific strategy logic (momentum, mean reversion, etc.)
            - Handle multiple instruments
            - Simulate order fills realistically
            - Account for slippage and market impact
        """
        trades = []
        equity_curve = [config.starting_capital]
        current_capital = config.starting_capital

        # Simplified momentum strategy simulation
        if config.strategy_type == "momentum":
            lookback = config.parameters.get("lookback_period", 20)

            for instrument, data in market_data.items():
                if len(data) < lookback + 1:
                    continue

                for i in range(lookback, len(data)):
                    # Calculate momentum
                    current_price = data[i].price
                    past_price = data[i - lookback].price
                    momentum = (current_price - past_price) / past_price

                    threshold = Decimal(str(config.parameters.get("momentum_threshold", 0.02)))

                    # Generate signal
                    if momentum > threshold:
                        # Buy signal
                        quantity = Decimal("1")  # Simplified position sizing
                        entry_price = current_price
                        commission = entry_price * quantity * config.commission_rate

                        # Simulate exit after holding period
                        exit_idx = min(i + 5, len(data) - 1)
                        exit_price = data[exit_idx].price

                        pnl = (exit_price - entry_price) * quantity - commission * 2
                        return_pct = pnl / (entry_price * quantity)

                        current_capital += pnl
                        equity_curve.append(current_capital)

                        trades.append({
                            "instrument": instrument,
                            "entry_time": data[i].timestamp,
                            "exit_time": data[exit_idx].timestamp,
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "quantity": quantity,
                            "pnl": pnl,
                            "return_pct": return_pct,
                            "commission": commission * 2,
                        })

        # Ensure equity curve has at least ending value
        if len(equity_curve) == 1:
            equity_curve.append(current_capital)

        return trades, equity_curve

    def _calculate_daily_returns(self, equity_curve: list[Decimal]) -> list[Decimal]:
        """
        Calculate daily returns from equity curve.

        Args:
            equity_curve: Portfolio value over time

        Returns:
            List of daily returns
        """
        if len(equity_curve) < 2:
            return []

        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] > 0:
                daily_return = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                returns.append(daily_return)

        return returns

    async def compare_strategies(
        self,
        configs: list[BacktestConfig],
    ) -> list[BacktestResult]:
        """
        Run backtests for multiple strategy configurations and compare.

        Args:
            configs: List of backtest configurations

        Returns:
            List of BacktestResults sorted by Sharpe ratio (descending)
        """
        results = []

        for config in configs:
            try:
                result = await self.run_backtest(config)
                results.append(result)
            except BacktestEngineError as e:
                # Log error but continue with other configs
                print(f"Backtest failed for {config.strategy_type}: {e}")

        # Sort by Sharpe ratio (best first)
        results.sort(key=lambda r: r.performance.sharpe_ratio, reverse=True)

        return results

"""BacktestEngine Service - Application Use Case Layer.

Orchestrates backtesting strategies against historical data.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from src.algo_trading.adapters.models.market_data import MarketDataDocument
from src.algo_trading.domain.analytics.performance_calculator import PerformanceCalculator, PerformanceResult, Trade

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtesting configuration."""

    strategy_type: str
    parameters: dict
    instruments: list[str]
    period_start: datetime
    period_end: datetime
    starting_capital: Decimal
    commission_rate: Decimal = Decimal('0.001')  # 0.1% per trade


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


class BacktestEngine:
    """
    Application service for strategy backtesting.
    Simulates strategy execution on historical data.
    """

    def __init__(self, calculator: PerformanceCalculator | None = None) -> None:
        """
        Initialize BacktestEngine.

        Args:
            calculator: Domain calculator for performance metrics
        """
        self.calculator = calculator or PerformanceCalculator()

    async def run_backtest(self, config: BacktestConfig) -> BacktestResult:
        """
        Run backtest for strategy configuration.

        Args:
            config: Backtesting configuration

        Returns:
            BacktestResult with performance metrics

        Raises:
            BacktestEngineError: If backtest fails
        """
        start_time = datetime.now(timezone.utc)
        market_data = await self._load_market_data(
            instruments=config.instruments,
            period_start=config.period_start,
            period_end=config.period_end,
        )

        if not market_data:
            raise BacktestEngineError('No market data found for backtest period')

        trades, equity_curve = await self._simulate_strategy(config, market_data)
        trade_objs = [Trade(pnl=t['pnl'], return_pct=t['return_pct']) for t in trades]
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

        end_time = datetime.now(timezone.utc)
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
    ) -> dict[str, list[MarketDataDocument]]:
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

        logger.info(f"Loading market data for {len(instruments)} instruments from {period_start} to {period_end}")

        for instrument in instruments:
            market_data = (
                await MarketDataDocument.find(
                    MarketDataDocument.instrument == instrument,
                    MarketDataDocument.timestamp >= period_start,
                    MarketDataDocument.timestamp <= period_end,
                )
                .sort('timestamp')
                .to_list()
            )

            data_by_instrument[instrument] = market_data
            logger.info(f"  {instrument}: loaded {len(market_data)} data points")

        return data_by_instrument

    async def _simulate_strategy(
        self,
        config: BacktestConfig,
        market_data: dict[str, list[MarketDataDocument]],
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
        if config.strategy_type == 'momentum':
            lookback = config.parameters.get('lookback_period', 20)
            threshold = Decimal(str(config.parameters.get('momentum_threshold', 0.02)))

            logger.debug(f"Momentum strategy: lookback={lookback}, threshold={threshold}")

            for instrument, data in market_data.items():
                logger.debug(f"Processing {instrument}: {len(data)} data points")

                if len(data) < lookback + 1:
                    logger.warning(f"  Skipping {instrument}: insufficient data ({len(data)} < {lookback + 1})")
                    continue

                signals_generated = 0
                for i in range(lookback, len(data)):
                    current_price = data[i].close_price
                    past_price = data[i - lookback].close_price
                    momentum = (current_price - past_price) / past_price

                    if momentum > threshold:
                        signals_generated += 1
                        quantity = Decimal('1')
                        entry_price = current_price
                        commission = entry_price * quantity * config.commission_rate

                        exit_idx = min(i + 5, len(data) - 1)
                        exit_price = data[exit_idx].close_price

                        pnl = (exit_price - entry_price) * quantity - commission * 2
                        return_pct = pnl / (entry_price * quantity)

                        current_capital += pnl
                        equity_curve.append(current_capital)

                        trades.append(
                            {
                                'instrument': instrument,
                                'entry_time': data[i].timestamp,
                                'exit_time': data[exit_idx].timestamp,
                                'entry_price': entry_price,
                                'exit_price': exit_price,
                                'quantity': quantity,
                                'pnl': pnl,
                                'return_pct': return_pct,
                                'commission': commission * 2,
                            },
                        )

                instrument_trades = [t for t in trades if t['instrument'] == instrument]
                logger.info(f"  {instrument}: {signals_generated} signals → {len(instrument_trades)} trades")

            logger.info(f"Total: {len(trades)} trades executed")

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
        min_len_equity_curve = 2
        if len(equity_curve) < min_len_equity_curve:
            return []

        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] > 0:
                daily_return = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                returns.append(daily_return)

        return returns

    async def compare_strategies(self, configs: list[BacktestConfig]) -> list[BacktestResult]:
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
            except BacktestEngineError:
                # Log error but continue with other configs
                pass

        # Sort by Sharpe ratio (best first)
        results.sort(key=lambda r: r.performance.sharpe_ratio, reverse=True)

        return results

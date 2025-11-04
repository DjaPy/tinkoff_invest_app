"""Scheduled Metrics Service - Background Jobs for Performance Analytics.

This service runs periodic tasks to calculate and store performance metrics snapshots.
Follows aiomisc Service pattern for integration with application lifecycle.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from aiomisc import PeriodicService

from src.algo_trading.adapters.models import StrategyStatusEnum, TradingStrategyDocument
from src.algo_trading.services.performance_analytics import PerformanceAnalytics, PerformanceAnalyticsError


logger = logging.getLogger(__name__)


class ScheduledMetricsService(PeriodicService):
    """
    Periodic service for calculating daily performance metrics snapshots.

    Runs daily to calculate performance metrics for all active strategies.
    Uses PerformanceAnalytics service with caching to avoid duplicate calculations.
    """

    interval = 24 * 60 * 60  # 24 hours in seconds

    def __init__(self, run_at_startup: bool = False) -> None:
        """
        Initialize scheduled metrics service.

        Args:
            run_at_startup: If True, run the job immediately on startup (default: False)
        """
        super().__init__(interval=self.interval)
        self.run_at_startup = run_at_startup
        self._startup_executed = False

    async def callback(self) -> None:
        """
        Execute daily metrics calculation for all active strategies.

        Called by aiomisc PeriodicService on schedule.
        Iterates through all ACTIVE and DEPLOYED strategies and calculates
        yesterday's performance metrics.
        """
        logger.info('Starting scheduled metrics calculation job')

        try:
            # Execute on startup if configured
            if self.run_at_startup and not self._startup_executed:
                await self._calculate_metrics_for_all_strategies()
                self._startup_executed = True
                return

            # Regular scheduled execution
            await self._calculate_metrics_for_all_strategies()

        except Exception:
            logger.exception('Scheduled metrics calculation failed')

    async def _calculate_metrics_for_all_strategies(self) -> None:
        """Calculate metrics for all active strategies."""
        # Calculate for yesterday (full day)
        period_end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        period_start = period_end - timedelta(days=1)

        # Find all active or deployed strategies
        strategies = await TradingStrategyDocument.find(
            (TradingStrategyDocument.status == StrategyStatusEnum.ACTIVE)
            | (TradingStrategyDocument.status == StrategyStatusEnum.DEPLOYED),
        ).to_list()

        if not strategies:
            logger.info('No active strategies found for metrics calculation')
            return

        logger.info(f'Found {len(strategies)} active strategies, calculating metrics for {period_start.date()}')

        perf_analytics = PerformanceAnalytics()
        success_count = 0
        error_count = 0

        for strategy in strategies:
            try:
                metrics = await perf_analytics.calculate_strategy_performance(
                    strategy_id=strategy.strategy_id,
                    period_start=period_start,
                    period_end=period_end,
                    cache_ttl_hours=24,  # Cache for 24 hours (until next run)
                    force_recalculate=False,  # Use cache if available
                )

                logger.info(
                    f'Calculated metrics for strategy {strategy.strategy_id} '
                    f'(return: {metrics.total_return:.2%}, sharpe: {metrics.sharpe_ratio:.2f})',
                )
                success_count += 1

            except PerformanceAnalyticsError as e:
                logger.warning(f'Failed to calculate metrics for strategy {strategy.strategy_id}: {e}')
                error_count += 1
            except Exception:
                logger.exception(f'Unexpected error calculating metrics for strategy {strategy.strategy_id}')
                error_count += 1

            # Small delay to avoid overwhelming database
            await asyncio.sleep(0.1)

        logger.info(
            f'Scheduled metrics calculation completed: '
            f'{success_count} successful, {error_count} errors',
        )
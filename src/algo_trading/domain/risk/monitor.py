"""Real-time Risk Monitor - Domain Layer.

Continuously monitors trading activity and enforces risk limits in real-time.
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.algo_trading.domain.risk.risk_evaluator import (
    RiskEvaluator,
    RiskLimits,
    RiskViolation,
)

logger = logging.getLogger(__name__)


class RiskMonitorError(Exception):
    """Risk monitoring operation failed."""


RiskViolationCallback = Callable[[UUID, RiskViolation], Awaitable[None]]


class RiskMonitor:
    """
    Real-time risk monitor for trading strategies.

    Continuously evaluates risk metrics and triggers callbacks when violations occur.
    """

    def __init__(self, risk_evaluator: RiskEvaluator | None = None) -> None:
        """
        Initialize risk monitor.

        Args:
            risk_evaluator: Risk evaluation engine (optional, creates default if None)
        """
        self.risk_evaluator = risk_evaluator or RiskEvaluator()
        self._violation_callbacks: list[RiskViolationCallback] = []
        self._monitoring_enabled: dict[UUID, bool] = {}
        self._last_check: dict[UUID, datetime] = {}
        self._violation_count: dict[UUID, int] = {}

    def on_violation(self, callback: RiskViolationCallback) -> None:
        """
        Register callback to be called when risk violation occurs.

        Args:
            callback: Async function to call on violation
        """
        self._violation_callbacks.append(callback)

    def enable_monitoring(self, strategy_id: UUID) -> None:
        """
        Enable risk monitoring for strategy.

        Args:
            strategy_id: Strategy to monitor
        """
        self._monitoring_enabled[strategy_id] = True
        self._last_check[strategy_id] = datetime.utcnow()
        self._violation_count[strategy_id] = 0

    def disable_monitoring(self, strategy_id: UUID) -> None:
        """
        Disable risk monitoring for strategy.

        Args:
            strategy_id: Strategy to stop monitoring
        """
        self._monitoring_enabled[strategy_id] = False

    def is_monitoring(self, strategy_id: UUID) -> bool:
        """
        Check if strategy is being monitored.

        Args:
            strategy_id: Strategy ID

        Returns:
            True if monitoring enabled
        """
        return self._monitoring_enabled.get(strategy_id, False)

    async def check_position_risk(
        self,
        strategy_id: UUID,
        position_size: Decimal,
        risk_limits: RiskLimits,
    ) -> list[RiskViolation]:
        """
        Check position size against risk limits.

        Args:
            strategy_id: Strategy ID
            position_size: Current position size
            risk_limits: Risk limits to enforce

        Returns:
            List of risk violations (empty if no violations)
        """
        if not self.is_monitoring(strategy_id):
            return []

        violations = []

        # Check position size limit
        if self.risk_evaluator.exceeds_position_limit(position_size, risk_limits):
            violation = RiskViolation(
                rule='max_position_size',
                current_value=position_size,
                limit_value=risk_limits.max_position_size,
                severity='high',
            )
            violations.append(violation)
            await self._handle_violation(strategy_id, violation)

        self._last_check[strategy_id] = datetime.utcnow()
        return violations

    async def check_portfolio_risk(
        self,
        strategy_id: UUID,
        portfolio_value: Decimal,
        risk_limits: RiskLimits,
    ) -> list[RiskViolation]:
        """
        Check portfolio value against risk limits.

        Args:
            strategy_id: Strategy ID
            portfolio_value: Current portfolio value
            risk_limits: Risk limits to enforce

        Returns:
            List of risk violations
        """
        if not self.is_monitoring(strategy_id):
            return []

        violations = []

        # Check portfolio value limit
        if self.risk_evaluator.exceeds_portfolio_limit(portfolio_value, risk_limits):
            violation = RiskViolation(
                rule='max_portfolio_value',
                current_value=portfolio_value,
                limit_value=risk_limits.max_portfolio_value,
                severity='high',
            )
            violations.append(violation)
            await self._handle_violation(strategy_id, violation)

        self._last_check[strategy_id] = datetime.utcnow()
        return violations

    async def check_drawdown_risk(
        self,
        strategy_id: UUID,
        current_drawdown: Decimal,
        risk_limits: RiskLimits,
    ) -> list[RiskViolation]:
        """
        Check drawdown against risk limits.

        Args:
            strategy_id: Strategy ID
            current_drawdown: Current drawdown percentage (negative value)
            risk_limits: Risk limits to enforce

        Returns:
            List of risk violations
        """
        if not self.is_monitoring(strategy_id):
            return []

        violations = []

        # Check max drawdown limit
        if self.risk_evaluator.exceeds_drawdown_limit(current_drawdown, risk_limits):
            violation = RiskViolation(
                rule='max_drawdown_percent',
                current_value=current_drawdown,
                limit_value=risk_limits.max_drawdown_percent,
                severity='critical',
            )
            violations.append(violation)
            await self._handle_violation(strategy_id, violation)

        self._last_check[strategy_id] = datetime.utcnow()
        return violations

    async def check_daily_loss_risk(
        self,
        strategy_id: UUID,
        daily_pnl: Decimal,
        risk_limits: RiskLimits,
    ) -> list[RiskViolation]:
        """
        Check daily P&L against risk limits.

        Args:
            strategy_id: Strategy ID
            daily_pnl: Current daily P&L
            risk_limits: Risk limits to enforce

        Returns:
            List of risk violations
        """
        if not self.is_monitoring(strategy_id):
            return []

        violations = []

        # Check daily loss limit (daily_pnl is negative for losses)
        if self.risk_evaluator.exceeds_daily_loss_limit(daily_pnl, risk_limits):
            violation = RiskViolation(
                rule='daily_loss_limit',
                current_value=daily_pnl,
                limit_value=risk_limits.daily_loss_limit,
                severity='critical',
            )
            violations.append(violation)
            await self._handle_violation(strategy_id, violation)

        self._last_check[strategy_id] = datetime.utcnow()
        return violations

    async def check_order_rate_risk(
        self,
        strategy_id: UUID,
        orders_today: int,
        risk_limits: RiskLimits,
    ) -> list[RiskViolation]:
        """
        Check order rate against risk limits.

        Args:
            strategy_id: Strategy ID
            orders_today: Number of orders placed today
            risk_limits: Risk limits to enforce

        Returns:
            List of risk violations
        """
        if not self.is_monitoring(strategy_id):
            return []

        violations = []

        # Check max orders per day limit
        if self.risk_evaluator.exceeds_order_rate_limit(orders_today, risk_limits):
            violation = RiskViolation(
                rule='max_orders_per_day',
                current_value=Decimal(str(orders_today)),
                limit_value=Decimal(str(risk_limits.max_orders_per_day)),
                severity='medium',
            )
            violations.append(violation)
            await self._handle_violation(strategy_id, violation)

        self._last_check[strategy_id] = datetime.utcnow()
        return violations

    async def check_all_risks(
        self,
        strategy_id: UUID,
        position_size: Decimal,
        portfolio_value: Decimal,
        current_drawdown: Decimal,
        daily_pnl: Decimal,
        orders_today: int,
        risk_limits: RiskLimits,
    ) -> list[RiskViolation]:
        """
        Comprehensive risk check across all risk dimensions.

        Args:
            strategy_id: Strategy ID
            position_size: Current position size
            portfolio_value: Current portfolio value
            current_drawdown: Current drawdown percentage
            daily_pnl: Current daily P&L
            orders_today: Number of orders placed today
            risk_limits: Risk limits to enforce

        Returns:
            List of all risk violations
        """
        if not self.is_monitoring(strategy_id):
            return []

        all_violations: list[RiskViolation] = []

        # Check all risk dimensions
        all_violations.extend(await self.check_position_risk(strategy_id, position_size, risk_limits))
        all_violations.extend(await self.check_portfolio_risk(strategy_id, portfolio_value, risk_limits))
        all_violations.extend(await self.check_drawdown_risk(strategy_id, current_drawdown, risk_limits))
        all_violations.extend(await self.check_daily_loss_risk(strategy_id, daily_pnl, risk_limits))
        all_violations.extend(await self.check_order_rate_risk(strategy_id, orders_today, risk_limits))

        return all_violations

    async def _handle_violation(self, strategy_id: UUID, violation: RiskViolation) -> None:
        """
        Handle risk violation by incrementing count and calling callbacks.

        Args:
            strategy_id: Strategy that violated risk limits
            violation: The risk violation that occurred
        """
        self._violation_count[strategy_id] = self._violation_count.get(strategy_id, 0) + 1

        for callback in self._violation_callbacks:
            try:
                await callback(strategy_id, violation)
            except Exception:
                logger.error('callback monitor fail')

    def get_violation_count(self, strategy_id: UUID) -> int:
        """
        Get total number of violations for strategy.

        Args:
            strategy_id: Strategy ID

        Returns:
            Total violation count
        """
        return self._violation_count.get(strategy_id, 0)

    def get_last_check_time(self, strategy_id: UUID) -> datetime | None:
        """
        Get last check time for strategy.

        Args:
            strategy_id: Strategy ID

        Returns:
            Last check timestamp or None if never checked
        """
        return self._last_check.get(strategy_id)

    def reset_violation_count(self, strategy_id: UUID) -> None:
        """
        Reset violation count for strategy.

        Args:
            strategy_id: Strategy ID
        """
        self._violation_count[strategy_id] = 0

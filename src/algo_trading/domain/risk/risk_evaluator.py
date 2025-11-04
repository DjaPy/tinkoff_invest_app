"""Risk Evaluation Domain Logic - Hexagonal Architecture Domain Layer.

Pure business logic for risk assessment, independent of infrastructure.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskLimits:
    """Risk control parameters."""

    max_position_size: Decimal
    max_portfolio_value: Decimal
    stop_loss_percent: Decimal
    max_drawdown_percent: Decimal
    daily_loss_limit: Decimal
    max_orders_per_day: int


@dataclass(frozen=True)
class PositionRisk:
    """Current position risk metrics."""

    current_position_size: Decimal
    current_portfolio_value: Decimal
    current_drawdown_percent: Decimal
    daily_loss: Decimal
    orders_today: int


@dataclass(frozen=True)
class OrderProposal:
    """Proposed order for risk evaluation."""

    instrument: str
    quantity: Decimal
    estimated_price: Decimal
    side: str  # 'buy' or 'sell'


@dataclass(frozen=True)
class RiskEvaluationResult:
    """Risk evaluation outcome."""

    approved: bool
    reason: str | None = None
    violated_limits: list[str] | None = None

    def __post_init__(self) -> None:
        """Ensure violated_limits is a list."""
        if self.violated_limits is None:
            object.__setattr__(self, 'violated_limits', [])


@dataclass(frozen=True)
class RiskViolation:
    """Risk violation details for monitoring."""

    rule: str
    current_value: Decimal
    limit_value: Decimal
    severity: str  # 'low', 'medium', 'high', 'critical'


class RiskEvaluator:
    """
    Pure domain logic for pre-trade and post-trade risk evaluation.

    No infrastructure dependencies - only operates on domain objects.
    """

    @staticmethod
    def evaluate_order(order: OrderProposal, current_risk: PositionRisk, limits: RiskLimits) -> RiskEvaluationResult:
        """
        Evaluate if proposed order violates risk limits.

        Args:
            order: Proposed trade order
            current_risk: Current portfolio risk metrics
            limits: Risk control limits

        Returns:
            RiskEvaluationResult with approval decision
        """
        violations = []

        # Check position size limit
        proposed_position = current_risk.current_position_size
        if order.side == 'buy':
            proposed_position += order.quantity
        else:
            proposed_position -= order.quantity

        if abs(proposed_position) > limits.max_position_size:
            violations.append(f'Position size {abs(proposed_position)} exceeds limit {limits.max_position_size}')

        # Check portfolio value limit
        order_value = order.quantity * order.estimated_price
        proposed_portfolio_value = current_risk.current_portfolio_value + order_value

        if proposed_portfolio_value > limits.max_portfolio_value:
            violations.append(f'Portfolio value {proposed_portfolio_value} exceeds limit {limits.max_portfolio_value}')

        # Check daily order limit
        if current_risk.orders_today >= limits.max_orders_per_day:
            violations.append(f'Daily order limit {limits.max_orders_per_day} already reached')

        # Check daily loss limit
        if abs(current_risk.daily_loss) >= limits.daily_loss_limit:
            violations.append(f'Daily loss {abs(current_risk.daily_loss)} exceeds limit {limits.daily_loss_limit}')

        # Check drawdown limit
        if abs(current_risk.current_drawdown_percent) >= limits.max_drawdown_percent:
            violations.append(
                f'Drawdown {abs(current_risk.current_drawdown_percent)} exceeds limit {limits.max_drawdown_percent}',
            )

        if violations:
            return RiskEvaluationResult(approved=False, reason='; '.join(violations), violated_limits=violations)

        return RiskEvaluationResult(approved=True)

    @staticmethod
    def calculate_stop_loss_price(entry_price: Decimal, stop_loss_percent: Decimal, side: str) -> Decimal:
        """
        Calculate stop-loss trigger price.

        Args:
            entry_price: Entry price for position
            stop_loss_percent: Stop-loss percentage (0.05 = 5%)
            side: 'buy' (long) or 'sell' (short)

        Returns:
            Stop-loss trigger price
        """
        if side == 'buy':
            # Long position - stop loss below entry
            return entry_price * (Decimal('1') - stop_loss_percent)
        # Short position - stop loss above entry
        return entry_price * (Decimal('1') + stop_loss_percent)

    @staticmethod
    def is_stop_loss_triggered(
        current_price: Decimal,
        entry_price: Decimal,
        stop_loss_percent: Decimal,
        side: str,
    ) -> bool:
        """
        Check if stop-loss condition is triggered.

        Args:
            current_price: Current market price
            entry_price: Entry price for position
            stop_loss_percent: Stop-loss percentage
            side: 'buy' (long) or 'sell' (short)

        Returns:
            True if stop-loss triggered
        """
        stop_loss_price = RiskEvaluator.calculate_stop_loss_price(entry_price, stop_loss_percent, side)

        if side == 'buy':
            # Long position - triggered if price drops below stop loss
            return current_price <= stop_loss_price
        # Short position - triggered if price rises above stop loss
        return current_price >= stop_loss_price

    @staticmethod
    def calculate_position_risk_percent(position_value: Decimal, portfolio_value: Decimal) -> Decimal:
        """
        Calculate position as percentage of portfolio.

        Args:
            position_value: Market value of position
            portfolio_value: Total portfolio value

        Returns:
            Position risk as percentage (0.05 = 5%)
        """
        if portfolio_value == 0:
            return Decimal('0')

        return position_value / portfolio_value

    @staticmethod
    def calculate_drawdown(peak_value: Decimal, current_value: Decimal) -> Decimal:
        """
        Calculate drawdown from peak.

        Args:
            peak_value: Historical peak portfolio value
            current_value: Current portfolio value

        Returns:
            Drawdown as negative percentage
        """
        if peak_value == 0:
            return Decimal('0')

        drawdown = (current_value - peak_value) / peak_value
        return min(drawdown, Decimal('0'))  # Ensure non-positive

    @staticmethod
    def exceeds_position_limit(position_size: Decimal, limits: RiskLimits) -> bool:
        """Check if position size exceeds limit."""
        return abs(position_size) > limits.max_position_size

    @staticmethod
    def exceeds_portfolio_limit(portfolio_value: Decimal, limits: RiskLimits) -> bool:
        """Check if portfolio value exceeds limit."""
        return portfolio_value > limits.max_portfolio_value

    @staticmethod
    def exceeds_drawdown_limit(current_drawdown: Decimal, limits: RiskLimits) -> bool:
        """Check if drawdown exceeds limit (drawdown is negative)."""
        return abs(current_drawdown) >= limits.max_drawdown_percent

    @staticmethod
    def exceeds_daily_loss_limit(daily_pnl: Decimal, limits: RiskLimits) -> bool:
        """Check if daily loss exceeds limit (daily_pnl is negative for losses)."""
        return abs(daily_pnl) >= limits.daily_loss_limit and daily_pnl < 0

    @staticmethod
    def exceeds_order_rate_limit(orders_today: int, limits: RiskLimits) -> bool:
        """Check if order rate exceeds limit."""
        return orders_today >= limits.max_orders_per_day

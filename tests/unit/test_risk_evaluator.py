"""Unit tests for risk control domain logic (T080).

Tests cover:
1. Order evaluation against risk limits (position size, portfolio value, daily limits)
2. Stop-loss price calculations (long and short positions)
3. Stop-loss trigger detection
4. Position risk percentage calculations
5. Drawdown calculations
6. Individual limit check functions

These tests focus on pure domain logic without infrastructure dependencies.
"""

from decimal import Decimal

from src.algo_trading.domain.risk.risk_evaluator import (
    OrderProposal,
    PositionRisk,
    RiskEvaluator,
    RiskLimits,
)


async def test_evaluate_order_approved_within_all_limits():
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('5000'),
        current_portfolio_value=Decimal('500000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('1000'),
        orders_today=50,
    )

    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('1000'),
        estimated_price=Decimal('150.00'),
        side='buy',
    )

    result = RiskEvaluator.evaluate_order(order, current_risk, limits)

    assert result.approved is True
    assert result.reason is None
    assert result.violated_limits == []


async def test_evaluate_order_rejected_position_size_exceeded():
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('9500'),
        current_portfolio_value=Decimal('500000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('1000'),
        orders_today=50,
    )

    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('1000'),
        estimated_price=Decimal('150.00'),
        side='buy',
    )

    result = RiskEvaluator.evaluate_order(order, current_risk, limits)

    assert result.approved is False
    assert 'Position size' in result.reason
    assert 'exceeds limit' in result.reason
    assert len(result.violated_limits) == 1


async def test_evaluate_order_rejected_portfolio_value_exceeded():
    limits = RiskLimits(
        max_position_size=Decimal('100000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('5000'),
        current_portfolio_value=Decimal('950000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('1000'),
        orders_today=50,
    )

    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('1000'),
        estimated_price=Decimal('100.00'),  # 1000 * 100 = 100,000
        side='buy',
    )

    result = RiskEvaluator.evaluate_order(order, current_risk, limits)

    assert result.approved is False
    assert 'Portfolio value' in result.reason
    assert 'exceeds limit' in result.reason


async def test_evaluate_order_rejected_daily_order_limit_reached():
    limits = RiskLimits(
        max_position_size=Decimal('100000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('5000'),
        current_portfolio_value=Decimal('500000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('1000'),
        orders_today=100,  # Already at limit
    )

    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('100'),
        estimated_price=Decimal('150.00'),
        side='buy',
    )

    result = RiskEvaluator.evaluate_order(order, current_risk, limits)

    assert result.approved is False
    assert 'Daily order limit' in result.reason
    assert 'already reached' in result.reason


async def test_evaluate_order_rejected_daily_loss_limit_exceeded():
    limits = RiskLimits(
        max_position_size=Decimal('100000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('5000'),
        current_portfolio_value=Decimal('500000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('-10000'),  # Already at loss limit
        orders_today=50,
    )

    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('100'),
        estimated_price=Decimal('150.00'),
        side='buy',
    )

    result = RiskEvaluator.evaluate_order(order, current_risk, limits)

    assert result.approved is False
    assert 'Daily loss' in result.reason
    assert 'exceeds limit' in result.reason


async def test_evaluate_order_rejected_drawdown_limit_exceeded():
    limits = RiskLimits(
        max_position_size=Decimal('100000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('5000'),
        current_portfolio_value=Decimal('500000'),
        current_drawdown_percent=Decimal('-0.20'),
        daily_loss=Decimal('1000'),
        orders_today=50,
    )

    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('100'),
        estimated_price=Decimal('150.00'),
        side='buy',
    )

    result = RiskEvaluator.evaluate_order(order, current_risk, limits)

    assert result.approved is False
    assert 'Drawdown' in result.reason
    assert 'exceeds limit' in result.reason


async def test_evaluate_order_rejected_multiple_violations():
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('9500'),
        current_portfolio_value=Decimal('500000'),
        current_drawdown_percent=Decimal('-0.20'),
        daily_loss=Decimal('-10000'),
        orders_today=100,
    )

    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('1000'),
        estimated_price=Decimal('150.00'),
        side='buy',
    )

    result = RiskEvaluator.evaluate_order(order, current_risk, limits)

    assert result.approved is False
    assert len(result.violated_limits) >= 3
    assert 'Position size' in result.reason
    assert 'Daily order limit' in result.reason


async def test_evaluate_order_sell_side_reduces_position():
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('8000'),
        current_portfolio_value=Decimal('500000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('1000'),
        orders_today=50,
    )

    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('2000'),
        estimated_price=Decimal('150.00'),
        side='sell',
    )

    result = RiskEvaluator.evaluate_order(order, current_risk, limits)

    assert result.approved is True


async def test_calculate_stop_loss_price_long_position():
    entry_price = Decimal('100.00')
    stop_loss_percent = Decimal('0.05')  # 5%
    side = 'buy'

    stop_loss_price = RiskEvaluator.calculate_stop_loss_price(entry_price, stop_loss_percent, side)

    assert stop_loss_price == Decimal('95.00')  # 100 - 5%


async def test_calculate_stop_loss_price_short_position():
    """Test stop-loss price calculation for short (sell) position."""
    entry_price = Decimal('100.00')
    stop_loss_percent = Decimal('0.05')
    side = 'sell'

    stop_loss_price = RiskEvaluator.calculate_stop_loss_price(entry_price, stop_loss_percent, side)

    assert stop_loss_price == Decimal('105.00')


async def test_is_stop_loss_triggered_long_below_threshold():
    """Test stop-loss triggered for long position when price drops below threshold."""
    current_price = Decimal('94.00')
    entry_price = Decimal('100.00')
    stop_loss_percent = Decimal('0.05')
    side = 'buy'

    triggered = RiskEvaluator.is_stop_loss_triggered(current_price, entry_price, stop_loss_percent, side)

    assert triggered is True


async def test_is_stop_loss_not_triggered_long_above_threshold():
    """Test stop-loss not triggered for long position when price stays above threshold."""
    current_price = Decimal('96.00')
    entry_price = Decimal('100.00')
    stop_loss_percent = Decimal('0.05')
    side = 'buy'

    triggered = RiskEvaluator.is_stop_loss_triggered(current_price, entry_price, stop_loss_percent, side)

    assert triggered is False


async def test_is_stop_loss_triggered_short_above_threshold():
    """Test stop-loss triggered for short position when price rises above threshold."""
    current_price = Decimal('106.00')
    entry_price = Decimal('100.00')
    stop_loss_percent = Decimal('0.05')
    side = 'sell'

    triggered = RiskEvaluator.is_stop_loss_triggered(current_price, entry_price, stop_loss_percent, side)

    assert triggered is True


async def test_is_stop_loss_not_triggered_short_below_threshold():
    """Test stop-loss not triggered for short position when price stays below threshold."""
    current_price = Decimal('104.00')
    entry_price = Decimal('100.00')
    stop_loss_percent = Decimal('0.05')
    side = 'sell'

    triggered = RiskEvaluator.is_stop_loss_triggered(current_price, entry_price, stop_loss_percent, side)

    assert triggered is False


async def test_is_stop_loss_triggered_exact_threshold():
    entry_price = Decimal('100.00')
    stop_loss_percent = Decimal('0.05')
    stop_loss_price = Decimal('95.00')
    side = 'buy'

    triggered = RiskEvaluator.is_stop_loss_triggered(stop_loss_price, entry_price, stop_loss_percent, side)

    assert triggered is True


async def test_calculate_position_risk_percent():
    position_value = Decimal('50000')
    portfolio_value = Decimal('1000000')

    risk_percent = RiskEvaluator.calculate_position_risk_percent(position_value, portfolio_value)

    assert risk_percent == Decimal('0.05')  # 5%


async def test_calculate_position_risk_percent_zero_portfolio():
    position_value = Decimal('50000')
    portfolio_value = Decimal('0')

    risk_percent = RiskEvaluator.calculate_position_risk_percent(position_value, portfolio_value)

    assert risk_percent == Decimal('0')


async def test_calculate_drawdown_from_peak():
    """Test drawdown calculation from peak value."""
    peak_value = Decimal('1000000')
    current_value = Decimal('850000')

    drawdown = RiskEvaluator.calculate_drawdown(peak_value, current_value)

    assert drawdown == Decimal('-0.15')  # -15%


async def test_calculate_drawdown_at_peak():
    """Test drawdown calculation when at peak (no drawdown)."""
    peak_value = Decimal('1000000')
    current_value = Decimal('1000000')

    drawdown = RiskEvaluator.calculate_drawdown(peak_value, current_value)

    assert drawdown == Decimal('0')


async def test_calculate_drawdown_above_peak():
    """Test drawdown calculation returns zero when above peak."""
    peak_value = Decimal('1000000')
    current_value = Decimal('1100000')

    drawdown = RiskEvaluator.calculate_drawdown(peak_value, current_value)

    assert drawdown == Decimal('0')  # No drawdown when above peak


async def test_calculate_drawdown_zero_peak():
    """Test drawdown calculation with zero peak value."""
    peak_value = Decimal('0')
    current_value = Decimal('850000')

    drawdown = RiskEvaluator.calculate_drawdown(peak_value, current_value)

    assert drawdown == Decimal('0')


async def test_exceeds_position_limit_true():
    """Test position size exceeds limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    position_size = Decimal('15000')

    assert RiskEvaluator.exceeds_position_limit(position_size, limits) is True


async def test_exceeds_position_limit_false():
    """Test position size within limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    position_size = Decimal('5000')

    assert RiskEvaluator.exceeds_position_limit(position_size, limits) is False


async def test_exceeds_portfolio_limit_true():
    """Test portfolio value exceeds limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    portfolio_value = Decimal('1500000')

    assert RiskEvaluator.exceeds_portfolio_limit(portfolio_value, limits) is True


async def test_exceeds_portfolio_limit_false():
    """Test portfolio value within limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    portfolio_value = Decimal('500000')

    assert RiskEvaluator.exceeds_portfolio_limit(portfolio_value, limits) is False


async def test_exceeds_drawdown_limit_true():
    """Test drawdown exceeds limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    current_drawdown = Decimal('-0.20')  # 20% drawdown

    assert RiskEvaluator.exceeds_drawdown_limit(current_drawdown, limits) is True


async def test_exceeds_drawdown_limit_false():
    """Test drawdown within limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    current_drawdown = Decimal('-0.10')  # 10% drawdown

    assert RiskEvaluator.exceeds_drawdown_limit(current_drawdown, limits) is False


async def test_exceeds_daily_loss_limit_true():
    """Test daily loss exceeds limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    daily_pnl = Decimal('-15000')

    assert RiskEvaluator.exceeds_daily_loss_limit(daily_pnl, limits) is True


async def test_exceeds_daily_loss_limit_false_within_limit():
    """Test daily loss within limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    daily_pnl = Decimal('-5000')  # Loss within limit

    assert RiskEvaluator.exceeds_daily_loss_limit(daily_pnl, limits) is False


async def test_exceeds_daily_loss_limit_false_profit():
    """Test daily profit does not exceed loss limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    daily_pnl = Decimal('15000')  # Profit (positive)

    assert RiskEvaluator.exceeds_daily_loss_limit(daily_pnl, limits) is False


async def test_exceeds_order_rate_limit_true():
    """Test order rate exceeds limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    orders_today = 150

    assert RiskEvaluator.exceeds_order_rate_limit(orders_today, limits) is True


async def test_exceeds_order_rate_limit_false():
    """Test order rate within limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    orders_today = 50

    assert RiskEvaluator.exceeds_order_rate_limit(orders_today, limits) is False


async def test_exceeds_order_rate_limit_exact_limit():
    """Test order rate at exact limit."""
    limits = RiskLimits(
        max_position_size=Decimal('10000'),
        max_portfolio_value=Decimal('1000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('10000'),
        max_orders_per_day=100,
    )

    orders_today = 100

    assert RiskEvaluator.exceeds_order_rate_limit(orders_today, limits) is True

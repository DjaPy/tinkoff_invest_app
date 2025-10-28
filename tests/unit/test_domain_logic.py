"""Unit tests for domain logic (T079-T083 combined).

Tests cover:
- Risk evaluator validation logic
- Performance calculations
- Domain models and dataclasses

These tests focus on pure domain logic without infrastructure dependencies.
"""

from decimal import Decimal

import pytest

from src.algo_trading.domain.analytics.performance_calculator import (
    PerformanceCalculator,
    Trade,
)
from src.algo_trading.domain.risk.risk_evaluator import (
    OrderProposal,
    PositionRisk,
    RiskEvaluator,
    RiskLimits,
)


@pytest.mark.asyncio
async def test_risk_evaluator_approves_valid_order():
    """Test that risk evaluator approves orders within limits."""
    evaluator = RiskEvaluator()

    limits = RiskLimits(
        max_position_size=Decimal('1000'),
        max_portfolio_value=Decimal('50000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.10'),
        daily_loss_limit=Decimal('1000'),
        max_orders_per_day=20,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('500'),
        current_portfolio_value=Decimal('25000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('200'),
        orders_today=10,
    )

    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('100'),
        estimated_price=Decimal('150'),
        side='buy',
    )

    result = evaluator.evaluate_order(order, current_risk, limits)

    assert result.approved is True


@pytest.mark.asyncio
async def test_risk_evaluator_rejects_position_limit_violation():
    """Test that risk evaluator rejects orders exceeding position limits."""
    evaluator = RiskEvaluator()

    limits = RiskLimits(
        max_position_size=Decimal('1000'),
        max_portfolio_value=Decimal('50000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.10'),
        daily_loss_limit=Decimal('1000'),
        max_orders_per_day=20,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('950'),
        current_portfolio_value=Decimal('25000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('200'),
        orders_today=10,
    )

    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('100'),
        estimated_price=Decimal('150'),
        side='buy',
    )

    result = evaluator.evaluate_order(order, current_risk, limits)

    assert result.approved is False


# ==================== PERFORMANCE CALCULATOR TESTS ====================


@pytest.mark.asyncio
async def test_calculate_total_return():
    """Test total return calculation."""
    calculator = PerformanceCalculator()

    # Profit scenario
    total_return = calculator.calculate_total_return(
        starting_capital=Decimal('10000'),
        ending_capital=Decimal('12000'),
    )

    assert total_return == Decimal('0.20')  # 20% return

    # Loss scenario
    total_loss = calculator.calculate_total_return(
        starting_capital=Decimal('10000'),
        ending_capital=Decimal('8000'),
    )

    assert total_loss == Decimal('-0.20')  # -20% return


@pytest.mark.asyncio
async def test_calculate_max_drawdown():
    """Test maximum drawdown calculation."""
    calculator = PerformanceCalculator()

    equity_curve = [
        Decimal('10000'),
        Decimal('11000'),
        Decimal('12000'),
        Decimal('10500'),
        Decimal('9500'),
        Decimal('10000'),
    ]

    max_dd = calculator.calculate_max_drawdown(equity_curve)

    assert max_dd < Decimal('0')  # Drawdown should be negative


@pytest.mark.asyncio
async def test_calculate_max_drawdown_no_losses():
    """Test drawdown with increasing equity."""
    calculator = PerformanceCalculator()

    equity_curve = [
        Decimal('10000'),
        Decimal('11000'),
        Decimal('12000'),
        Decimal('13000'),
    ]

    max_dd = calculator.calculate_max_drawdown(equity_curve)

    assert max_dd == Decimal('0')


@pytest.mark.asyncio
async def test_calculate_volatility():
    """Test volatility calculation."""
    calculator = PerformanceCalculator()

    returns = [
        Decimal('0.02'),
        Decimal('-0.01'),
        Decimal('0.03'),
        Decimal('-0.02'),
        Decimal('0.01'),
    ]

    volatility = calculator.calculate_volatility(returns)

    assert volatility > Decimal('0')


@pytest.mark.asyncio
async def test_calculate_trade_statistics():
    """Test trade statistics calculation."""
    calculator = PerformanceCalculator()

    trades = [
        Trade(pnl=Decimal('100'), return_pct=Decimal('0.02')),
        Trade(pnl=Decimal('-50'), return_pct=Decimal('-0.01')),
        Trade(pnl=Decimal('200'), return_pct=Decimal('0.04')),
        Trade(pnl=Decimal('-100'), return_pct=Decimal('-0.02')),
    ]

    stats = calculator.calculate_trade_statistics(trades)

    # 2 wins out of 4 = 50% win rate
    assert stats.win_rate == Decimal('0.50')

    # Profit factor = gross profit / gross loss = 300 / 150 = 2.0
    assert stats.profit_factor == Decimal('2.00')

    # Average win = 300 / 2 = 150
    assert stats.avg_win == Decimal('150')


@pytest.mark.asyncio
async def test_calculate_sharpe_ratio():
    """Test Sharpe ratio calculation."""
    calculator = PerformanceCalculator()

    average_return = Decimal('0.001')  # 0.1% daily
    volatility = Decimal('0.02')  # 2% daily volatility
    risk_free_rate = Decimal('0.03')  # 3% annual

    sharpe = calculator.calculate_sharpe_ratio(
        average_return=average_return,
        volatility=volatility,
        risk_free_rate=risk_free_rate,
    )

    # Sharpe should be calculated
    assert isinstance(sharpe, Decimal)


# ==================== DOMAIN MODEL TESTS ====================


@pytest.mark.asyncio
async def test_risk_limits_dataclass():
    """Test RiskLimits dataclass creation."""
    limits = RiskLimits(
        max_position_size=Decimal('1000'),
        max_portfolio_value=Decimal('50000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.10'),
        daily_loss_limit=Decimal('1000'),
        max_orders_per_day=20,
    )

    assert limits.max_position_size == Decimal('1000')
    assert limits.stop_loss_percent == Decimal('0.05')


@pytest.mark.asyncio
async def test_position_risk_dataclass():
    """Test PositionRisk dataclass creation."""
    risk = PositionRisk(
        current_position_size=Decimal('500'),
        current_portfolio_value=Decimal('25000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('200'),
        orders_today=10,
    )

    assert risk.current_position_size == Decimal('500')
    assert risk.current_portfolio_value == Decimal('25000')


@pytest.mark.asyncio
async def test_trade_dataclass():
    """Test Trade dataclass creation."""
    trade = Trade(
        pnl=Decimal('150.50'),
        return_pct=Decimal('0.025'),
    )

    assert trade.pnl == Decimal('150.50')
    assert trade.return_pct == Decimal('0.025')


@pytest.mark.asyncio
async def test_order_proposal_dataclass():
    """Test OrderProposal dataclass creation."""
    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('100'),
        estimated_price=Decimal('150.75'),
        side='buy',
    )

    assert order.instrument == 'AAPL'
    assert order.quantity == Decimal('100')
    assert order.estimated_price == Decimal('150.75')
    assert order.side == 'buy'

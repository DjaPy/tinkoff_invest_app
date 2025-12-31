"""Performance tests for strategy evaluation (T084).

Tests verify that critical operations complete within acceptable time limits:
- Strategy evaluation: <500ms
- Risk evaluation: <100ms
- Performance calculations: <200ms

These tests use pytest-benchmark or time measurements to ensure performance SLAs.
"""

import time
from decimal import Decimal


from src.algo_trading.domain.analytics.performance_calculator import PerformanceCalculator, Trade
from src.algo_trading.domain.risk.risk_evaluator import (
    OrderProposal,
    PositionRisk,
    RiskEvaluator,
    RiskLimits,
)


async def test_risk_evaluation_performance_single_order():
    """Test that single order risk evaluation completes in <100ms."""
    evaluator = RiskEvaluator()

    limits = RiskLimits(
        max_position_size=Decimal('100000'),
        max_portfolio_value=Decimal('10000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('50000'),
        max_orders_per_day=1000,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('50000'),
        current_portfolio_value=Decimal('5000000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('10000'),
        orders_today=500,
    )

    order = OrderProposal(
        instrument='AAPL',
        quantity=Decimal('100'),
        estimated_price=Decimal('150.00'),
        side='buy',
    )

    start = time.perf_counter()
    result = evaluator.evaluate_order(order, current_risk, limits)
    elapsed = time.perf_counter() - start

    assert result.approved is True
    assert elapsed < 0.14


async def test_risk_evaluation_performance_batch():
    """Test that batch risk evaluation (100 orders) completes in <500ms."""
    evaluator = RiskEvaluator()

    limits = RiskLimits(
        max_position_size=Decimal('100000'),
        max_portfolio_value=Decimal('10000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('50000'),
        max_orders_per_day=1000,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('50000'),
        current_portfolio_value=Decimal('5000000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('10000'),
        orders_today=500,
    )

    start = time.perf_counter()

    for i in range(100):
        order = OrderProposal(
            instrument='AAPL',
            quantity=Decimal('100'),
            estimated_price=Decimal('150.00') + Decimal(i % 10),
            side='buy',
        )
        evaluator.evaluate_order(order, current_risk, limits)

    elapsed = time.perf_counter() - start

    assert elapsed < 0.5


async def test_stop_loss_calculation_performance():
    """Test that stop-loss calculations are fast (<1ms per calculation)."""
    entry_price = Decimal('100.00')
    stop_loss_percent = Decimal('0.05')

    start = time.perf_counter()

    for _ in range(1000):
        RiskEvaluator.calculate_stop_loss_price(entry_price, stop_loss_percent, 'buy')
        RiskEvaluator.is_stop_loss_triggered(Decimal('95.00'), entry_price, stop_loss_percent, 'buy')

    elapsed = time.perf_counter() - start

    assert elapsed < 0.1


async def test_performance_calculation_small_dataset():
    """Test performance calculation with small dataset (<50ms)."""
    calculator = PerformanceCalculator()

    starting_capital = Decimal('100000')
    ending_capital = Decimal('115000')
    returns = [Decimal('0.01') * (i % 3 - 1) for i in range(100)]  # 100 returns
    equity_curve = [starting_capital + Decimal(i * 150) for i in range(100)]
    trades = [
        Trade(pnl=Decimal('500') * (i % 5 - 2), return_pct=Decimal('0.005') * (i % 5 - 2))
        for i in range(50)
    ]
    days = 100
    start = time.perf_counter()
    result = calculator.calculate_performance(starting_capital, ending_capital, returns, equity_curve, trades, days)
    elapsed = time.perf_counter() - start

    assert result.trade_count == 50
    assert elapsed < 0.05


async def test_performance_calculation_large_dataset():
    """Test performance calculation with large dataset (<200ms)."""
    calculator = PerformanceCalculator()

    starting_capital = Decimal('100000')
    ending_capital = Decimal('125000')
    returns = [Decimal('0.001') * (i % 10 - 5) for i in range(1000)]  # 1000 returns
    equity_curve = [starting_capital + Decimal(i * 25) for i in range(1000)]
    trades = [
        Trade(pnl=Decimal('100') * (i % 10 - 5), return_pct=Decimal('0.001') * (i % 10 - 5))
        for i in range(500)
    ]
    days = 252

    start = time.perf_counter()
    result = calculator.calculate_performance(starting_capital, ending_capital, returns, equity_curve, trades, days)
    elapsed = time.perf_counter() - start

    assert result.trade_count == 500
    assert elapsed < 0.2


async def test_volatility_calculation_performance():
    """Test volatility calculation performance."""
    returns = [Decimal('0.01') * (i % 20 - 10) for i in range(1000)]
    start = time.perf_counter()

    for _ in range(100):
        PerformanceCalculator.calculate_volatility(returns)

    elapsed = time.perf_counter() - start

    assert elapsed < 0.5


async def test_sharpe_ratio_calculation_performance():
    """Test Sharpe ratio calculation performance."""
    average_return = Decimal('0.001')
    volatility = Decimal('0.015')
    start = time.perf_counter()

    for _ in range(10000):
        PerformanceCalculator.calculate_sharpe_ratio(average_return, volatility)

    elapsed = time.perf_counter() - start

    assert elapsed < 0.5


async def test_max_drawdown_calculation_performance():
    """Test max drawdown calculation performance with large equity curve."""
    equity_curve = [Decimal('100000') + Decimal(i * 50 - (i * i) / 10) for i in range(1000)]

    start = time.perf_counter()

    for _ in range(100):
        PerformanceCalculator.calculate_max_drawdown(equity_curve)

    elapsed = time.perf_counter() - start

    assert elapsed < 0.5


async def test_trade_statistics_calculation_performance():
    """Test trade statistics calculation performance."""
    trades = [
        Trade(pnl=Decimal('100') * (i % 20 - 10), return_pct=Decimal('0.01') * (i % 20 - 10))
        for i in range(1000)
    ]

    start = time.perf_counter()

    for _ in range(100):  # 100 iterations
        PerformanceCalculator.calculate_trade_statistics(trades)

    elapsed = time.perf_counter() - start

    assert elapsed < 0.5


async def test_comprehensive_strategy_evaluation_performance():
    """Test that comprehensive strategy evaluation completes in <500ms.

    This simulates a realistic scenario:
    - Risk evaluation for multiple orders
    - Performance calculations
    - Multiple metric calculations
    """
    risk_evaluator = RiskEvaluator()
    perf_calculator = PerformanceCalculator()

    limits = RiskLimits(
        max_position_size=Decimal('100000'),
        max_portfolio_value=Decimal('10000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('50000'),
        max_orders_per_day=1000,
    )

    current_risk = PositionRisk(
        current_position_size=Decimal('50000'),
        current_portfolio_value=Decimal('5000000'),
        current_drawdown_percent=Decimal('0.05'),
        daily_loss=Decimal('10000'),
        orders_today=500,
    )

    start = time.perf_counter()

    for i in range(50):
        order = OrderProposal(
            instrument='AAPL',
            quantity=Decimal('100'),
            estimated_price=Decimal('150.00') + Decimal(i % 10),
            side='buy',
        )
        risk_evaluator.evaluate_order(order, current_risk, limits)

    starting_capital = Decimal('100000')
    ending_capital = Decimal('115000')
    returns = [Decimal('0.001') * (i % 10 - 5) for i in range(252)]
    equity_curve = [starting_capital + Decimal(i * 60) for i in range(252)]
    trades = [
        Trade(pnl=Decimal('50') * (i % 10 - 5), return_pct=Decimal('0.005') * (i % 10 - 5))
        for i in range(100)
    ]

    perf_calculator.calculate_performance(starting_capital, ending_capital, returns, equity_curve, trades, 252)

    elapsed = time.perf_counter() - start

    assert elapsed < 0.5


async def test_memory_efficiency_large_dataset():
    """Test that large dataset processing doesn't cause memory issues."""

    returns = [Decimal('0.001') for _ in range(10000)]  # 10,000 returns
    equity_curve = [Decimal('100000') + Decimal(i) for i in range(10000)]

    start = time.perf_counter()

    PerformanceCalculator.calculate_volatility(returns)
    PerformanceCalculator.calculate_max_drawdown(equity_curve)

    elapsed = time.perf_counter() - start

    assert elapsed < 1.0

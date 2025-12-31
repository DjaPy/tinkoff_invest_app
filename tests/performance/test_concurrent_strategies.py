"""Load tests for concurrent strategy execution (T085).

Tests verify system behavior under concurrent load:
- Multiple strategies executing simultaneously
- Concurrent risk evaluations
- Concurrent performance calculations
- Resource contention and thread safety

These tests ensure the system can handle realistic production workloads.
"""

import asyncio
import time
from decimal import Decimal


from src.algo_trading.domain.analytics.performance_calculator import PerformanceCalculator, Trade
from src.algo_trading.domain.risk.risk_evaluator import (
    OrderProposal,
    PositionRisk,
    RiskEvaluator,
    RiskLimits,
)


async def test_concurrent_risk_evaluations_10_strategies():
    """Test concurrent risk evaluation for 10 strategies."""
    evaluator = RiskEvaluator()

    limits = RiskLimits(
        max_position_size=Decimal('100000'),
        max_portfolio_value=Decimal('10000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('50000'),
        max_orders_per_day=1000,
    )

    async def evaluate_strategy_orders(strategy_id: int):
        """Simulate a strategy evaluating 10 orders."""
        current_risk = PositionRisk(
            current_position_size=Decimal('50000') + Decimal(strategy_id * 1000),
            current_portfolio_value=Decimal('5000000'),
            current_drawdown_percent=Decimal('0.05'),
            daily_loss=Decimal('10000'),
            orders_today=500,
        )

        for i in range(10):
            order = OrderProposal(
                instrument=f'STOCK{strategy_id}',
                quantity=Decimal('100'),
                estimated_price=Decimal('150.00') + Decimal(i),
                side='buy',
            )
            evaluator.evaluate_order(order, current_risk, limits)

    start = time.perf_counter()

    tasks = [evaluate_strategy_orders(i) for i in range(10)]
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start

    assert elapsed < 1.0


async def test_concurrent_risk_evaluations_50_strategies():
    """Test concurrent risk evaluation for 50 strategies (heavy load)."""
    evaluator = RiskEvaluator()

    limits = RiskLimits(
        max_position_size=Decimal('100000'),
        max_portfolio_value=Decimal('10000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('50000'),
        max_orders_per_day=1000,
    )

    async def evaluate_strategy_orders(strategy_id: int):
        """Simulate a strategy evaluating 5 orders."""
        current_risk = PositionRisk(
            current_position_size=Decimal('50000'),
            current_portfolio_value=Decimal('5000000'),
            current_drawdown_percent=Decimal('0.05'),
            daily_loss=Decimal('10000'),
            orders_today=500,
        )

        for i in range(5):
            order = OrderProposal(
                instrument=f'STOCK{strategy_id}',
                quantity=Decimal('100'),
                estimated_price=Decimal('150.00'),
                side='buy',
            )
            evaluator.evaluate_order(order, current_risk, limits)

    start = time.perf_counter()

    tasks = [evaluate_strategy_orders(i) for i in range(50)]
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start
    assert elapsed < 2.0


async def test_concurrent_performance_calculations_10_strategies():
    """Test concurrent performance calculations for 10 strategies."""
    calculator = PerformanceCalculator()

    async def calculate_strategy_performance(strategy_number: int):
        """Calculate performance for a single strategy."""
        starting_capital = Decimal('100000')
        ending_capital = Decimal('100000') + Decimal(strategy_number * 1000)
        returns = [Decimal('0.001') * (i % 10 - 5) for i in range(100)]
        equity_curve = [starting_capital + Decimal(i * 50) for i in range(100)]
        trades = [
            Trade(pnl=Decimal('50') * (i % 10 - 5), return_pct=Decimal('0.005') * (i % 10 - 5))
            for i in range(50)
        ]

        calculator.calculate_performance(starting_capital, ending_capital, returns, equity_curve, trades, 100)

    start = time.perf_counter()

    tasks = [calculate_strategy_performance(i) for i in range(10)]
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start

    assert elapsed < 1.0


async def test_concurrent_performance_calculations_100_strategies():
    """Test concurrent performance calculations for 100 strategies (stress test)."""
    calculator = PerformanceCalculator()

    async def calculate_strategy_performance(strategy_id: int):
        """Calculate performance for a single strategy with smaller dataset."""
        starting_capital = Decimal('100000')
        ending_capital = Decimal('105000')
        returns = [Decimal('0.001') for _ in range(50)]
        equity_curve = [starting_capital + Decimal(i * 100) for i in range(50)]
        trades = [Trade(pnl=Decimal('100'), return_pct=Decimal('0.001')) for _ in range(20)]

        calculator.calculate_performance(starting_capital, ending_capital, returns, equity_curve, trades, 50)

    start = time.perf_counter()

    tasks = [calculate_strategy_performance(i) for i in range(100)]
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start

    assert elapsed < 3.0


async def test_mixed_concurrent_workload():
    """Test mixed workload: risk evaluation + performance calculation."""
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

    async def strategy_workload(strategy_id: int):
        """Simulate complete strategy workload: risk eval + perf calc."""
        current_risk = PositionRisk(
            current_position_size=Decimal('50000'),
            current_portfolio_value=Decimal('5000000'),
            current_drawdown_percent=Decimal('0.05'),
            daily_loss=Decimal('10000'),
            orders_today=500,
        )

        for i in range(5):
            order = OrderProposal(
                instrument=f'STOCK{strategy_id}',
                quantity=Decimal('100'),
                estimated_price=Decimal('150.00'),
                side='buy',
            )
            risk_evaluator.evaluate_order(order, current_risk, limits)

        # Performance calculation
        starting_capital = Decimal('100000')
        ending_capital = Decimal('105000')
        returns = [Decimal('0.001') for _ in range(50)]
        equity_curve = [starting_capital + Decimal(i * 100) for i in range(50)]
        trades = [Trade(pnl=Decimal('100'), return_pct=Decimal('0.001')) for _ in range(20)]

        perf_calculator.calculate_performance(starting_capital, ending_capital, returns, equity_curve, trades, 50)

    start = time.perf_counter()

    tasks = [strategy_workload(i) for i in range(20)]
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start

    assert elapsed < 2.0


async def test_throughput_order_evaluations_per_second():
    """Test system throughput: how many order evaluations per second."""
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

    count = 0
    start = time.perf_counter()

    while time.perf_counter() - start < 1.0:
        evaluator.evaluate_order(order, current_risk, limits)
        count += 1
    assert count > 10000


async def test_throughput_performance_calculations_per_second():
    """Test system throughput: performance calculations per second."""
    calculator = PerformanceCalculator()

    starting_capital = Decimal('100000')
    ending_capital = Decimal('105000')
    returns = [Decimal('0.001') for _ in range(50)]
    equity_curve = [starting_capital + Decimal(i * 100) for i in range(50)]
    trades = [Trade(pnl=Decimal('100'), return_pct=Decimal('0.001')) for _ in range(20)]

    count = 0
    start = time.perf_counter()

    while time.perf_counter() - start < 1.0:
        calculator.calculate_performance(starting_capital, ending_capital, returns, equity_curve, trades, 50)
        count += 1

    assert count > 100


async def test_scalability_linear_growth():
    """Test that execution time grows linearly with number of strategies."""
    evaluator = RiskEvaluator()

    limits = RiskLimits(
        max_position_size=Decimal('100000'),
        max_portfolio_value=Decimal('10000000'),
        stop_loss_percent=Decimal('0.05'),
        max_drawdown_percent=Decimal('0.15'),
        daily_loss_limit=Decimal('50000'),
        max_orders_per_day=1000,
    )

    async def evaluate_n_strategies(n: int) -> float:
        """Evaluate n strategies and return elapsed time."""
        async def evaluate_strategy(strategy_id: int):
            current_risk = PositionRisk(
                current_position_size=Decimal('50000'),
                current_portfolio_value=Decimal('5000000'),
                current_drawdown_percent=Decimal('0.05'),
                daily_loss=Decimal('10000'),
                orders_today=500,
            )

            for i in range(5):
                order = OrderProposal(
                    instrument=f'STOCK{strategy_id}',
                    quantity=Decimal('100'),
                    estimated_price=Decimal('150.00'),
                    side='buy',
                )
                evaluator.evaluate_order(order, current_risk, limits)

        start = time.perf_counter()
        tasks = [evaluate_strategy(i) for i in range(n)]
        await asyncio.gather(*tasks)
        return time.perf_counter() - start

    time_10 = await evaluate_n_strategies(10)
    time_20 = await evaluate_n_strategies(20)
    assert time_20 < time_10 * 3

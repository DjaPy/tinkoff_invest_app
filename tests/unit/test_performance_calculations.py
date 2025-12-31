"""Unit tests for performance calculation domain logic (T082).

Tests cover:
1. Total return calculation (profit, loss, zero scenarios)
2. Annualized return calculation (CAGR)
3. Volatility calculation (standard deviation)
4. Sharpe ratio calculation (risk-adjusted returns)
5. Maximum drawdown calculation
6. Trade statistics (win rate, profit factor, averages)
7. Comprehensive performance metrics

These tests focus on pure domain logic without infrastructure dependencies.
"""

from decimal import Decimal


from src.algo_trading.domain.analytics.performance_calculator import PerformanceCalculator, Trade



async def test_calculate_total_return_profit():
    """Test total return calculation with profit."""
    starting_capital = Decimal('100000')
    ending_capital = Decimal('115000')

    total_return = PerformanceCalculator.calculate_total_return(starting_capital, ending_capital)

    assert total_return == Decimal('0.15')  # 15% return


async def test_calculate_total_return_loss():
    """Test total return calculation with loss."""
    starting_capital = Decimal('100000')
    ending_capital = Decimal('85000')

    total_return = PerformanceCalculator.calculate_total_return(starting_capital, ending_capital)

    assert total_return == Decimal('-0.15')  # -15% loss


async def test_calculate_total_return_no_change():
    """Test total return calculation with no change."""
    starting_capital = Decimal('100000')
    ending_capital = Decimal('100000')

    total_return = PerformanceCalculator.calculate_total_return(starting_capital, ending_capital)

    assert total_return == Decimal('0')


async def test_calculate_total_return_zero_starting_capital():
    """Test total return with zero starting capital returns zero."""
    starting_capital = Decimal('0')
    ending_capital = Decimal('100000')

    total_return = PerformanceCalculator.calculate_total_return(starting_capital, ending_capital)

    assert total_return == Decimal('0')



async def test_calculate_annualized_return_one_year():
    """Test annualized return for exactly one year."""
    total_return = Decimal('0.20')  # 20% return
    days = 252  # Trading days in one year

    annualized = PerformanceCalculator.calculate_annualized_return(total_return, days)

    assert abs(annualized - Decimal('0.20')) < Decimal('0.001')  # Should be ~20%


async def test_calculate_annualized_return_half_year():
    """Test annualized return for half year."""
    total_return = Decimal('0.10')  # 10% in half year
    days = 126  # Half year

    annualized = PerformanceCalculator.calculate_annualized_return(total_return, days)

    # Should be higher when annualized
    assert annualized > Decimal('0.10')


async def test_calculate_annualized_return_zero_days():
    """Test annualized return with zero days returns zero."""
    total_return = Decimal('0.15')
    days = 0

    annualized = PerformanceCalculator.calculate_annualized_return(total_return, days)

    assert annualized == Decimal('0')


async def test_calculate_annualized_return_negative():
    """Test annualized return with negative total return."""
    total_return = Decimal('-0.20')  # -20% loss
    days = 252

    annualized = PerformanceCalculator.calculate_annualized_return(total_return, days)

    assert annualized < Decimal('0')



async def test_calculate_volatility_stable_returns():
    """Test volatility with stable returns."""
    returns = [Decimal('0.01')] * 10  # 1% every day

    volatility = PerformanceCalculator.calculate_volatility(returns)

    assert volatility == Decimal('0')  # Zero volatility for constant returns


async def test_calculate_volatility_varying_returns():
    """Test volatility with varying returns."""
    returns = [
        Decimal('0.02'),
        Decimal('-0.01'),
        Decimal('0.03'),
        Decimal('0.01'),
        Decimal('-0.02'),
    ]

    volatility = PerformanceCalculator.calculate_volatility(returns)

    assert volatility > Decimal('0')


async def test_calculate_volatility_single_return():
    """Test volatility with single return returns zero."""
    returns = [Decimal('0.05')]

    volatility = PerformanceCalculator.calculate_volatility(returns)

    assert volatility == Decimal('0')


async def test_calculate_volatility_empty_list():
    """Test volatility with empty list returns zero."""
    returns = []

    volatility = PerformanceCalculator.calculate_volatility(returns)

    assert volatility == Decimal('0')


async def test_calculate_sharpe_ratio_positive_returns():
    """Test Sharpe ratio with positive average returns."""
    average_return = Decimal('0.001')  # 0.1% daily
    volatility = Decimal('0.01')
    risk_free_rate = Decimal('0.03')  # 3% annual

    sharpe = PerformanceCalculator.calculate_sharpe_ratio(average_return, volatility, risk_free_rate)

    assert sharpe > Decimal('0')


async def test_calculate_sharpe_ratio_zero_volatility():
    """Test Sharpe ratio with zero volatility returns zero."""
    average_return = Decimal('0.01')
    volatility = Decimal('0')

    sharpe = PerformanceCalculator.calculate_sharpe_ratio(average_return, volatility)

    assert sharpe == Decimal('0')


async def test_calculate_sharpe_ratio_negative_returns():
    """Test Sharpe ratio with negative average returns."""
    average_return = Decimal('-0.001')  # Negative daily return
    volatility = Decimal('0.01')

    sharpe = PerformanceCalculator.calculate_sharpe_ratio(average_return, volatility)

    assert sharpe < Decimal('0')


async def test_calculate_sharpe_ratio_default_risk_free():
    """Test Sharpe ratio with default risk-free rate."""
    average_return = Decimal('0.001')
    volatility = Decimal('0.01')

    sharpe = PerformanceCalculator.calculate_sharpe_ratio(average_return, volatility)

    assert isinstance(sharpe, Decimal)


async def test_calculate_max_drawdown_with_loss():
    """Test max drawdown with declining equity."""
    equity_curve = [
        Decimal('100000'),
        Decimal('105000'),
        Decimal('98000'),  # Drawdown from peak
        Decimal('92000'),  # Larger drawdown
        Decimal('95000'),
    ]

    max_dd = PerformanceCalculator.calculate_max_drawdown(equity_curve)

    # Max drawdown from 105000 to 92000 = (92000-105000)/105000 = -0.123809...
    assert max_dd < Decimal('0')
    assert max_dd > Decimal('-0.15')


async def test_calculate_max_drawdown_no_losses():
    """Test max drawdown with only gains."""
    equity_curve = [
        Decimal('100000'),
        Decimal('105000'),
        Decimal('110000'),
        Decimal('115000'),
    ]

    max_dd = PerformanceCalculator.calculate_max_drawdown(equity_curve)

    assert max_dd == Decimal('0')


async def test_calculate_max_drawdown_single_value():
    """Test max drawdown with single value returns zero."""
    equity_curve = [Decimal('100000')]

    max_dd = PerformanceCalculator.calculate_max_drawdown(equity_curve)

    assert max_dd == Decimal('0')


async def test_calculate_max_drawdown_empty_list():
    """Test max drawdown with empty list returns zero."""
    equity_curve = []

    max_dd = PerformanceCalculator.calculate_max_drawdown(equity_curve)

    assert max_dd == Decimal('0')


async def test_calculate_trade_statistics_all_wins():
    """Test trade statistics with all winning trades."""
    trades = [
        Trade(pnl=Decimal('100'), return_pct=Decimal('0.01')),
        Trade(pnl=Decimal('200'), return_pct=Decimal('0.02')),
        Trade(pnl=Decimal('150'), return_pct=Decimal('0.015')),
    ]

    stats = PerformanceCalculator.calculate_trade_statistics(trades)

    assert stats.win_rate == Decimal('1.0')  # 100% win rate
    assert stats.profit_factor == Decimal('0')  # No losses
    assert stats.avg_win == Decimal('150')  # (100+200+150)/3
    assert stats.avg_loss == Decimal('0')
    assert stats.largest_win == Decimal('200')
    assert stats.largest_loss == Decimal('0')


async def test_calculate_trade_statistics_all_losses():
    """Test trade statistics with all losing trades."""
    trades = [
        Trade(pnl=Decimal('-100'), return_pct=Decimal('-0.01')),
        Trade(pnl=Decimal('-200'), return_pct=Decimal('-0.02')),
        Trade(pnl=Decimal('-150'), return_pct=Decimal('-0.015')),
    ]

    stats = PerformanceCalculator.calculate_trade_statistics(trades)

    assert stats.win_rate == Decimal('0')  # 0% win rate
    assert stats.profit_factor == Decimal('0')  # No wins
    assert stats.avg_win == Decimal('0')
    assert stats.avg_loss == Decimal('150')  # (100+200+150)/3
    assert stats.largest_win == Decimal('0')
    assert stats.largest_loss == Decimal('-200')


async def test_calculate_trade_statistics_mixed_trades():
    """Test trade statistics with winning and losing trades."""
    trades = [
        Trade(pnl=Decimal('200'), return_pct=Decimal('0.02')),
        Trade(pnl=Decimal('-100'), return_pct=Decimal('-0.01')),
        Trade(pnl=Decimal('150'), return_pct=Decimal('0.015')),
        Trade(pnl=Decimal('-50'), return_pct=Decimal('-0.005')),
    ]

    stats = PerformanceCalculator.calculate_trade_statistics(trades)

    assert stats.win_rate == Decimal('0.5')  # 50% win rate (2 wins / 4 total)
    assert stats.profit_factor == Decimal('2.333333333333333333333333333')  # 350/150
    assert stats.avg_win == Decimal('175')  # (200+150)/2
    assert stats.avg_loss == Decimal('75')  # (100+50)/2
    assert stats.largest_win == Decimal('200')
    assert stats.largest_loss == Decimal('-100')


async def test_calculate_trade_statistics_empty_trades():
    """Test trade statistics with no trades."""
    trades = []

    stats = PerformanceCalculator.calculate_trade_statistics(trades)

    assert stats.win_rate == Decimal('0')
    assert stats.profit_factor == Decimal('0')
    assert stats.avg_win == Decimal('0')
    assert stats.avg_loss == Decimal('0')
    assert stats.largest_win == Decimal('0')
    assert stats.largest_loss == Decimal('0')


async def test_calculate_performance_comprehensive():
    """Test comprehensive performance calculation."""
    starting_capital = Decimal('100000')
    ending_capital = Decimal('115000')
    returns = [
        Decimal('0.01'),
        Decimal('-0.005'),
        Decimal('0.015'),
        Decimal('0.002'),
        Decimal('-0.003'),
    ]
    equity_curve = [
        Decimal('100000'),
        Decimal('101000'),
        Decimal('100500'),
        Decimal('102000'),
        Decimal('102200'),
        Decimal('115000'),
    ]
    trades = [
        Trade(pnl=Decimal('500'), return_pct=Decimal('0.005')),
        Trade(pnl=Decimal('-200'), return_pct=Decimal('-0.002')),
        Trade(pnl=Decimal('1000'), return_pct=Decimal('0.01')),
    ]
    days = 252

    result = PerformanceCalculator.calculate_performance(
        starting_capital,
        ending_capital,
        returns,
        equity_curve,
        trades,
        days,
    )

    assert result.total_return == Decimal('0.15')
    assert result.trade_count == 3
    assert result.win_rate > Decimal('0')
    assert result.volatility > Decimal('0')
    assert result.max_drawdown <= Decimal('0')


async def test_calculate_performance_zero_trades():
    """Test performance calculation with no trades."""
    starting_capital = Decimal('100000')
    ending_capital = Decimal('100000')
    returns = []
    equity_curve = [Decimal('100000')]
    trades = []
    days = 0

    result = PerformanceCalculator.calculate_performance(
        starting_capital,
        ending_capital,
        returns,
        equity_curve,
        trades,
        days,
    )

    assert result.total_return == Decimal('0')
    assert result.trade_count == 0
    assert result.win_rate == Decimal('0')
    assert result.volatility == Decimal('0')

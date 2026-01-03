"""Integration Test: Backtesting Workflow (Scenario 5).

Validates user story: Backtest strategies against historical data before
live deployment.
"""
from http import HTTPStatus

from src.algo_trading.enums import StrategyTypeEnum


async def test_backtest_workflow(client, config, mongo_connection, mock_auth):
    """
    Integration test for backtesting workflow.
    """
    backtest_config = {
        'strategy_type': StrategyTypeEnum.MOMENTUM.value,
        'parameters': {
            'lookback_period': 20,
            'momentum_threshold': 0.02,
            'instruments': ['AAPL', 'MSFT', 'GOOGL'],
            'position_size': 100,
        },
        'instruments': ['AAPL', 'MSFT', 'GOOGL'],
        'start_date': '2024-01-01T00:00:00',
        'end_date': '2024-12-31T00:00:00',
        'initial_capital': '50000',
        'risk_controls': {
            'max_position_size': '10000',
            'max_portfolio_value': '100000',
            'stop_loss_percent': '0.05',
            'max_drawdown_percent': '0.20',
            'daily_loss_limit': '2000',
            'max_orders_per_day': 50,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
        json=backtest_config,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        backtest_results = await response.json()
        assert 'total_return' in backtest_results or 'results' in backtest_results
        assert 'sharpe_ratio' in backtest_results or 'metrics' in backtest_results



async def test_backtest_with_different_strategy_types(client, mongo_connection, config, mock_auth):
    """
    Test backtesting with different strategy types.

    Validates backtest engine handles various strategies.
    """
    test_configs = [
        {
            'strategy_type': StrategyTypeEnum.MOMENTUM.value,
            'parameters': {
                'lookback_period': 20,
                'momentum_threshold': 0.02,
                'instruments': ['AAPL'],
                'position_size': 100,
            },
            'instruments': ['AAPL'],
        },
        {
            'strategy_type': StrategyTypeEnum.MEAN_REVERSION.value,
            'parameters': {
                'moving_average_period': 20,
                'std_dev_threshold': 2.0,
                'instruments': ['MSFT'],
                'position_size': 100,
            },
            'instruments': ['MSFT'],
        },
    ]

    for test_params in test_configs:
        backtest_config = {
            'strategy_type': test_params['strategy_type'],
            'parameters': test_params['parameters'],
            'instruments': test_params['instruments'],
            'start_date': '2024-01-01T00:00:00',
            'end_date': '2024-03-31T00:00:00',
            'initial_capital': '25000',
            'risk_controls': {
                'max_position_size': '5000',
                'max_portfolio_value': '50000',
                'stop_loss_percent': '0.05',
                'max_drawdown_percent': '0.20',
                'daily_loss_limit': '1000',
                'max_orders_per_day': 50,
                'trading_hours_start': '09:30:00',
                'trading_hours_end': '16:00:00',
                'enabled': True,
            },
        }

        async with client.post(
            url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
            json=backtest_config,
            headers={'Authorization': 'Bearer test-token'},
        ) as response:
            assert response.status == HTTPStatus.OK



async def test_backtest_validation(client, config, mock_auth):
    """
    Test backtest request validation.

    Validates proper error handling for invalid backtest configurations (end_date before start_date).
    """
    invalid_config = {
        'strategy_type': StrategyTypeEnum.MOMENTUM.value,
        'parameters': {
            'lookback_period': 20,
            'momentum_threshold': 0.02,
            'instruments': ['AAPL'],
            'position_size': 100,
        },
        'instruments': ['AAPL'],
        'start_date': '2024-12-31T00:00:00',  # end_date before start_date
        'end_date': '2024-01-01T00:00:00',
        'initial_capital': '50000',
        'risk_controls': {
            'max_position_size': '10000',
            'max_portfolio_value': '100000',
            'stop_loss_percent': '0.05',
            'max_drawdown_percent': '0.20',
            'daily_loss_limit': '2000',
            'max_orders_per_day': 50,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
        json=invalid_config,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        # Should return 400 Bad Request for end_date <= start_date (see analytics.py:384-385)
        assert response.status == HTTPStatus.BAD_REQUEST

"""Integration Test: Backtesting Workflow (Scenario 5).

Validates user story: Backtest strategies against historical data before
live deployment.
"""

from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_backtest_workflow(client, config, mongo_connection):
    """
    Integration test for backtesting workflow.

    Steps:
    1. Submit backtest request with historical parameters
    2. Verify backtest executes successfully
    3. Analyze backtest results
    """
    # Step 1: Submit backtest request
    backtest_config = {
        'strategy_config': {
            'strategy_type': 'momentum',
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'position_size': '100',
        },
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
        'initial_capital': '50000',
        'instruments': ['AAPL', 'MSFT', 'GOOGL'],
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
        json=backtest_config,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        backtest_results = await response.json()

        # Step 2 & 3: Verify backtest results structure
        # Results should include performance metrics
        assert 'total_return' in backtest_results or 'results' in backtest_results
        assert 'sharpe_ratio' in backtest_results or 'metrics' in backtest_results


@pytest.mark.asyncio
async def test_backtest_with_different_strategy_types(client, config):
    """
    Test backtesting with different strategy types.

    Validates backtest engine handles various strategies.
    """
    strategy_types = [
        {
            'strategy_type': 'momentum',
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'position_size': '100',
            'instruments': 'AAPL',
        },
        {
            'strategy_type': 'mean_reversion',
            'moving_average_period': '20',
            'std_dev_threshold': '2',
            'instruments': 'MSFT',
        },
    ]

    for strategy_config in strategy_types:
        backtest_config = {
            'strategy_config': strategy_config,
            'start_date': '2024-01-01',
            'end_date': '2024-03-31',
            'initial_capital': '25000',
            'instruments': ['AAPL'] if 'AAPL' in strategy_config.get('instruments', '') else ['MSFT'],
        }

        async with client.post(
            url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
            json=backtest_config,
            headers={'Authorization': 'Bearer test-token'},
        ) as response:
            assert response.status == HTTPStatus.OK


@pytest.mark.asyncio
async def test_backtest_validation(client, config):
    """
    Test backtest request validation.

    Validates proper error handling for invalid backtest configurations.
    """
    # Invalid: end_date before start_date
    invalid_config = {
        'strategy_config': {
            'strategy_type': 'momentum',
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'position_size': '100',
        },
        'start_date': '2024-12-31',
        'end_date': '2024-01-01',  # Before start_date
        'initial_capital': '50000',
        'instruments': ['AAPL'],
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest',
        json=invalid_config,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        # Should fail with validation error
        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY

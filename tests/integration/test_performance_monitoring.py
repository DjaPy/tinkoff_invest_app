"""Integration Test: Performance Monitoring (Scenario 3).

Validates user story: Monitor real-time strategy performance and analyze
historical results.
"""

from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_performance_monitoring_and_analytics(client, config, mongo_connection):
    """
    Integration test for performance monitoring workflow.

    Steps:
    1. Create and start a strategy
    2. Get real-time performance metrics
    3. View trade analytics
    4. Check drawdown analysis
    5. Get portfolio summary
    """
    # Step 1: Create and start strategy
    strategy_data = {
        'name': 'Performance Monitoring Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'instruments': 'AAPL,MSFT,GOOGL',
            'position_size': '100',
        },
        'risk_controls': {
            'max_position_size': '1000',
            'max_portfolio_value': '50000',
            'stop_loss_percent': '0.05',
            'max_drawdown_percent': '0.10',
            'daily_loss_limit': '1000',
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
        },
        'created_by': 'test_user',
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        json=strategy_data,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.CREATED
        created = await response.json()
        strategy_id = created['strategy_id']

    # Start strategy
    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK

    # Step 2: Get real-time performance metrics
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/performance?period=1d',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        performance = await response.json()

        # Verify performance metrics structure
        assert 'total_return' in performance or 'metrics' in performance

    # Step 3: View trade analytics
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/trades?period=1d',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        trades = await response.json()

        # Verify trade analytics structure
        assert 'trades' in trades or isinstance(trades, list)

    # Step 4: Check drawdown analysis
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/drawdown?period=7d',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        drawdown = await response.json()

        # Verify drawdown analysis structure
        assert 'max_drawdown' in drawdown or 'drawdown' in drawdown

    # Step 5: Get portfolio summary
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/portfolio/summary?period=1d',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        summary = await response.json()

        # Verify portfolio summary structure
        assert 'total_value' in summary or 'portfolio' in summary or 'summary' in summary


@pytest.mark.asyncio
async def test_performance_metrics_for_inactive_strategy(client, config, mongo_connection):
    """
    Test performance metrics for strategy that hasn't executed any trades.

    Validates graceful handling of empty performance data.
    """
    # Create strategy but don't start it
    strategy_data = {
        'name': 'Inactive Performance Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'instruments': 'AAPL',
            'position_size': '100',
        },
        'risk_controls': {
            'max_position_size': '1000',
            'max_portfolio_value': '50000',
            'stop_loss_percent': '0.05',
            'max_drawdown_percent': '0.10',
            'daily_loss_limit': '1000',
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
        },
        'created_by': 'test_user',
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        json=strategy_data,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.CREATED
        created = await response.json()
        strategy_id = created['strategy_id']

    # Get performance metrics for inactive strategy
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/performance?period=1d',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        # Should return OK with empty or zero metrics
        assert response.status == HTTPStatus.OK

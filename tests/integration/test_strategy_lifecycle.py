"""Integration Test: Strategy Lifecycle Management (Scenario 4).

Validates user story: Pause, resume, and stop trading strategies as needed.
"""

from http import HTTPStatus

import pytest

from src.algo_trading.adapters.models import StrategyStatus


@pytest.mark.asyncio
async def test_complete_strategy_lifecycle(client, config, mongo_connection):
    """
    Integration test for complete strategy lifecycle workflow.

    Steps:
    1. Create strategy (INACTIVE)
    2. Start strategy (ACTIVE)
    3. Pause strategy (PAUSED)
    4. Resume strategy (ACTIVE)
    5. Stop strategy (STOPPED)
    """
    # Step 1: Create strategy
    strategy_data = {
        'name': 'Lifecycle Test Strategy',
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
        assert created['status'] == StrategyStatus.INACTIVE.value

    # Step 2: Start strategy
    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        started = await response.json()
        assert started['status'] == StrategyStatus.ACTIVE.value

    # Step 3: Pause strategy
    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/pause',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        paused = await response.json()
        assert paused['status'] == StrategyStatus.PAUSED.value

    # Verify strategy is paused
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        status = await response.json()
        assert status['status'] == StrategyStatus.PAUSED.value

    # Step 4: Resume strategy (start from paused)
    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        resumed = await response.json()
        assert resumed['status'] == StrategyStatus.ACTIVE.value

    # Step 5: Stop strategy (emergency stop)
    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/stop',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        stopped = await response.json()
        assert stopped['status'] == StrategyStatus.STOPPED.value

    # Verify final state
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        final = await response.json()
        assert final['status'] == StrategyStatus.STOPPED.value


@pytest.mark.asyncio
async def test_invalid_state_transitions(client, config, mongo_connection):
    """
    Test that invalid state transitions are rejected.

    Validates state machine enforcement.
    """
    # Create strategy
    strategy_data = {
        'name': 'Invalid Transition Strategy',
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

    # Try to pause inactive strategy (should fail)
    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/pause',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        # Should fail with conflict or bad request
        assert response.status in [HTTPStatus.CONFLICT, HTTPStatus.BAD_REQUEST]


@pytest.mark.asyncio
async def test_strategy_deletion(client, config, mongo_connection):
    """
    Test strategy deletion workflow.

    Validates cleanup and resource management.
    """
    # Create strategy
    strategy_data = {
        'name': 'Delete Test Strategy',
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

    # Delete strategy
    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.NO_CONTENT

    # Verify strategy is deleted
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.NOT_FOUND

"""Integration Test: Strategy Deployment (Scenario 1).

Validates user story: Create and deploy algorithmic trading strategies
that automatically execute trades based on predefined rules.
"""

from http import HTTPStatus

import pytest

from src.algo_trading.adapters.models import StrategyStatusEnum, StrategyTypeEnum


@pytest.mark.asyncio
async def test_create_and_deploy_trading_strategy(client, config, mongo_connection):
    """
    Integration test for complete strategy deployment workflow.

    Steps:
    1. Create a new momentum strategy
    2. Verify strategy creation and configuration
    3. Start the strategy
    4. Verify strategy is active with trading session
    """
    # Step 1: Create a new momentum strategy
    strategy_data = {
        'name': 'Simple Momentum Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'instruments': 'AAPL,MSFT',
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
            'enabled': True,
        },
        'created_by': 'test_user',
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        json=strategy_data,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.CREATED
        created_strategy = await response.json()

        # Verify strategy creation
        assert 'strategy_id' in created_strategy
        assert created_strategy['name'] == 'Simple Momentum Strategy'
        assert created_strategy['strategy_type'] == StrategyTypeEnum.MOMENTUM.value
        assert created_strategy['status'] == StrategyStatusEnum.INACTIVE.value

        strategy_id = created_strategy['strategy_id']

    # Step 2: Verify strategy details
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        strategy_details = await response.json()

        # Verify configuration persisted correctly
        assert strategy_details['strategy_id'] == strategy_id
        assert strategy_details['parameters']['lookback_period'] == '20'
        assert strategy_details['parameters']['momentum_threshold'] == '0.02'
        assert strategy_details['risk_controls']['max_position_size'] == '1000'
        assert strategy_details['risk_controls']['stop_loss_percent'] == '0.05'
        assert strategy_details['status'] == StrategyStatusEnum.INACTIVE.value

    # Step 3: Start the strategy
    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        activated_strategy = await response.json()

        # Verify status changed to active
        assert activated_strategy['status'] == StrategyStatusEnum.ACTIVE.value
        assert 'session_id' in activated_strategy or 'message' in activated_strategy

    # Step 4: Verify strategy is active
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        active_strategy = await response.json()

        # Final verification
        assert active_strategy['status'] == StrategyStatusEnum.ACTIVE.value
        assert active_strategy['strategy_id'] == strategy_id


@pytest.mark.asyncio
async def test_strategy_deployment_with_invalid_parameters(client, config):
    """
    Test strategy creation fails with invalid parameters.

    Validates error handling for missing required parameters.
    """
    # Missing required momentum parameters
    invalid_strategy_data = {
        'name': 'Invalid Momentum Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            # Missing lookback_period, momentum_threshold, instruments
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
        json=invalid_strategy_data,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        # Should fail with validation error
        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_strategy_deployment_with_invalid_risk_controls(client, config):
    """
    Test strategy creation fails with invalid risk controls.

    Validates risk control validation (e.g., stop_loss_percent > 1.0).
    """
    invalid_risk_strategy = {
        'name': 'Invalid Risk Strategy',
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
            'stop_loss_percent': '1.5',  # Invalid: > 1.0
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
        json=invalid_risk_strategy,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        # Should fail with validation error
        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        error_data = await response.json()
        assert 'detail' in error_data


@pytest.mark.asyncio
async def test_cannot_start_already_active_strategy(client, config, mongo_connection):
    """
    Test that starting an already active strategy fails appropriately.

    Validates state transition rules.
    """
    # First create and start a strategy
    strategy_data = {
        'name': 'Test Active Strategy',
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

    # Create strategy
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

    # Try to start again - should fail with invalid state transition
    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        # Should fail with conflict or bad request
        assert response.status in [HTTPStatus.CONFLICT, HTTPStatus.BAD_REQUEST]

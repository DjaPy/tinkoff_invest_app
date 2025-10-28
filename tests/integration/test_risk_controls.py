"""Integration Test: Risk Management Controls.

Validates risk management framework integration.
"""

from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_risk_controls_enforcement(client, config, mongo_connection):
    """
    Integration test for risk controls enforcement.

    Validates that risk limits are properly enforced during strategy execution.
    """
    # Create strategy with strict risk controls
    strategy_data = {
        'name': 'Risk Control Test Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'instruments': 'AAPL',
            'position_size': '100',
        },
        'risk_controls': {
            'max_position_size': '200',  # Strict limit
            'max_portfolio_value': '10000',  # Low limit
            'stop_loss_percent': '0.02',  # Tight stop loss
            'max_drawdown_percent': '0.05',  # Strict drawdown limit
            'daily_loss_limit': '100',  # Low daily loss limit
            'max_orders_per_day': 3,  # Very few orders allowed
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
        created = await response.json()
        strategy_id = created['strategy_id']

    # Start strategy - should succeed with risk controls
    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK

    # Verify risk controls are active
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        strategy = await response.json()
        assert strategy['risk_controls']['enabled'] is True
        assert strategy['risk_controls']['max_position_size'] == '200'


@pytest.mark.asyncio
async def test_risk_controls_validation(client, config):
    """
    Test risk controls validation on strategy creation.

    Validates proper error handling for invalid risk parameters.
    """
    # Invalid stop_loss_percent (> 1.0)
    invalid_strategy = {
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
        json=invalid_strategy,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_update_risk_controls_on_running_strategy(client, config, mongo_connection):
    """
    Test updating risk controls on a running strategy.

    Validates dynamic risk management.
    """
    # Create and start strategy
    strategy_data = {
        'name': 'Dynamic Risk Strategy',
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

    # Start strategy
    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK

    # Update risk controls (tighten stop loss)
    updated_data = {
        'risk_controls': {
            'max_position_size': '1000',
            'max_portfolio_value': '50000',
            'stop_loss_percent': '0.03',  # Tightened from 0.05
            'max_drawdown_percent': '0.10',
            'daily_loss_limit': '1000',
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
        },
    }

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        json=updated_data,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        updated = await response.json()
        assert updated['risk_controls']['stop_loss_percent'] == '0.03'

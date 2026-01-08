"""Integration Test: Risk Management Controls.

Validates risk management framework integration.
"""

from http import HTTPStatus

from src.algo_trading.adapters.models import TinkoffAccountType


async def test_risk_controls_enforcement(client, config, mongo_connection, mock_auth, create_tinkoff_account):
    """
    Integration test for risk controls enforcement.

    Validates that risk limits are properly enforced during strategy execution.
    """

    user_id = mock_auth

    await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)

    strategy_data = {
        'name': 'Risk Control Test Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'instruments': ['AAPL'],
            'position_size': '100',
        },
        'risk_controls': {
            'max_position_size': '200',
            'max_portfolio_value': '10000',
            'stop_loss_percent': '0.02',
            'max_drawdown_percent': '0.05',
            'daily_loss_limit': '100',
            'max_orders_per_day': 3,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
        'created_by': str(user_id),
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        json=strategy_data,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.CREATED
        created = await response.json()
        strategy_id = created['strategy_id']

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        strategy = await response.json()
        assert strategy['risk_controls']['enabled'] is True
        assert strategy['risk_controls']['max_position_size'] == '200'



async def test_risk_controls_validation(client, config, mock_auth, create_tinkoff_account):
    """
    Test risk controls validation on strategy creation.

    Validates proper error handling for invalid risk parameters.
    """
    user_id = mock_auth
    await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)

    invalid_strategy = {
        'name': 'Invalid Risk Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'instruments': ['AAPL'],
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
        'created_by': str(user_id),
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        json=invalid_strategy,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY



async def test_update_risk_controls_on_running_strategy(client, config, mock_auth, create_tinkoff_account):
    """
    Test updating risk controls on a running strategy.

    Validates dynamic risk management.
    """

    await create_tinkoff_account(user_id=mock_auth, account_type=TinkoffAccountType.SANDBOX)

    strategy_data = {
        'name': 'Dynamic Risk Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'instruments': ['AAPL'],
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

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK

    updated_data = {
        'risk_controls': {
            'max_position_size': '1000',
            'max_portfolio_value': '50000',
            'stop_loss_percent': '0.03',
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

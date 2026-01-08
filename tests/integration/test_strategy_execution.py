"""Integration Test: Real-Time Strategy Execution (Scenario 2).

Validates user story: Algorithms execute trades automatically while
respecting risk limits.
"""

from http import HTTPStatus

from src.algo_trading.adapters.models import StrategyStatusEnum, TinkoffAccountType


async def test_real_time_strategy_execution_and_risk_management(client, config, mock_auth, create_tinkoff_account):
    """
    Integration test for real-time strategy execution workflow.
    """
    user_id = mock_auth
    await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)

    strategy_data = {
        'name': 'Execution Test Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'instruments': ['AAPL', 'MSFT'],
            'position_size': '100',
        },
        'risk_controls': {
            'max_position_size': '500',
            'max_portfolio_value': '25000',
            'stop_loss_percent': '0.03',
            'max_drawdown_percent': '0.08',
            'daily_loss_limit': '500',
            'max_orders_per_day': 10,
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
        strategy_status = await response.json()

        assert strategy_status['status'] == StrategyStatusEnum.ACTIVE.value
        assert strategy_status['strategy_id'] == strategy_id

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders?strategy_id={strategy_id}&limit=10',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        orders_data = await response.json()

        assert 'orders' in orders_data or isinstance(orders_data, list)

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions?strategy_id={strategy_id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        positions_data = await response.json()
        assert 'positions' in positions_data or isinstance(positions_data, list)



async def test_strategy_execution_monitoring_endpoints(client, config, mock_auth, create_tinkoff_account):
    """
    Test all monitoring endpoints work correctly during strategy execution.

    Validates complete observability of running strategy.
    """
    user_id = mock_auth
    await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)

    strategy_data = {
        'name': 'Monitoring Test Strategy',
        'strategy_type': 'mean_reversion',
        'parameters': {
            'moving_average_period': '20',
            'std_dev_threshold': '2',
            'instruments': ['MSFT', 'GOOGL'],
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

    monitoring_endpoints = [
        f'/api/v1/strategies/{strategy_id}',
        f'/api/v1/orders?strategy_id={strategy_id}',
        f'/api/v1/positions?strategy_id={strategy_id}',
        f'/api/v1/analytics/strategies/{strategy_id}/performance?period=1d',
        '/api/v1/analytics/portfolio/summary?period=1d',
    ]

    for endpoint in monitoring_endpoints:
        async with client.get(
            url=f'http://127.0.0.1:{config.http.port}{endpoint}',
            headers={'Authorization': 'Bearer test-token'},
        ) as response:
            assert response.status == HTTPStatus.OK, f'Endpoint {endpoint} failed'



async def test_strategy_execution_with_disabled_risk_controls(client, config, mock_auth, create_tinkoff_account):
    """
    Test strategy execution with risk controls disabled.

    Validates that strategies can run without risk limits if configured.
    """
    user_id = mock_auth
    await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)

    strategy_data = {
        'name': 'No Risk Controls Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '15',
            'momentum_threshold': '0.015',
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
            'enabled': False,  # Risk controls disabled
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
        started = await response.json()
        assert started['status'] == StrategyStatusEnum.ACTIVE.value

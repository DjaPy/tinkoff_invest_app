"""
Contract test for POST /api/v1/strategies endpoint

This test validates the API contract for creating new trading strategies.
It should FAIL until the actual endpoint implementation is complete.
"""

from decimal import Decimal

from starlette import status

from src.algo_trading.adapters.models.strategy import TradingStrategyDocument


async def test_post_strategies_creates_new_strategy(client, config, mongo_connection, mock_auth):
    """Test POST /api/v1/strategies creates a new trading strategy"""
    strategy_data = {
        'name': 'Test Momentum Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': 20,
            'momentum_threshold': 0.02,
            'instruments': ['AAPL', 'MSFT'],
            'position_size': 100,
        },
        'risk_controls': {
            'max_position_size': str(Decimal('1000')),
            'max_portfolio_value': str(Decimal('50000')),
            'stop_loss_percent': str(Decimal('0.05')),
            'max_drawdown_percent': str(Decimal('0.10')),
            'daily_loss_limit': str(Decimal('1000')),
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=strategy_data,
    ) as response:
        assert response.status == status.HTTP_201_CREATED
        assert 'application/json' in response.headers['content-type']

        data = await response.json()

        strategy = TradingStrategyDocument(**data)
        assert strategy.name == strategy_data['name']
        assert strategy.strategy_type.value == strategy_data['strategy_type']
        assert strategy.status.value == 'inactive'
        assert strategy.created_at is not None
        assert strategy.updated_at is not None
        assert strategy.risk_controls is not None


async def test_post_strategies_validates_required_fields(client, config, mock_auth):
    """Test POST /api/v1/strategies validates required fields"""
    invalid_data = {
        'name': 'Incomplete Strategy',
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=invalid_data,
    ) as response:
        assert response.status == 422
        assert 'application/problem+json' in response.headers['content-type']

        data = await response.json()
        assert 'invalid_params' in data
        assert 'title' in data
        assert data['status'] == 422


async def test_post_strategies_validates_risk_controls(client, config, services, mock_auth):
    """Test POST /api/v1/strategies validates risk control constraints"""

    strategy_data = {
        'name': 'Invalid Risk Strategy',
        'strategy_type': 'momentum',
        'parameters': {'lookback_period': 20},
        'risk_controls': {
            'max_position_size': 1000,
            'max_portfolio_value': 50000,
            'stop_loss_percent': 1.5,  # Invalid: > 1.0
            'max_drawdown_percent': 0.10,
            'daily_loss_limit': 1000,
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=strategy_data,
    ) as response:
        assert response.status == 422
        data = await response.json()
        assert 'invalid_params' in data or 'detail' in data


async def test_post_strategies_unauthorized_without_token(client, config, services):
    """Test POST /api/v1/strategies requires authentication"""

    strategy_data = {
        'name': 'Test Strategy',
        'strategy_type': 'momentum',
        'parameters': {'lookback_period': 20},
        'risk_controls': {
            'max_position_size': 1000,
            'max_portfolio_value': 50000,
            'stop_loss_percent': 0.05,
            'max_drawdown_percent': 0.10,
            'daily_loss_limit': 1000,
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Content-Type': 'application/json'},
        json=strategy_data,
    ) as response:
        assert response.status == 401
        data = await response.json()
        assert data['status'] == 401
        assert data['title'] == 'Unauthorized'

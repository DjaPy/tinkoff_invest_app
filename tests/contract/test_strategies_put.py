"""
Contract test for PUT /api/v1/strategies/{strategy_id} endpoint (T007)

This test validates the API contract for updating trading strategies.
It should FAIL until the actual endpoint implementation is complete.

Following TDD approach - tests written before implementation.
"""
from decimal import Decimal
from uuid import uuid4

import pytest
from starlette import status

from src.algo_trading.ports.api.v1.schemas.strategies_schema import TradingStrategyResponseSchema
from src.algo_trading.adapters.models.strategy import (
    MomentumParameters,
    StrategyTypeEnum,
)

async def test_put_strategy_updates_existing_strategy(client, config, mock_auth, create_trading_strategy):
    """Test PUT /api/v1/strategies/{strategy_id} updates an existing strategy"""

    original_strategy = await create_trading_strategy(
        name='Original Momentum Strategy',
        strategy_type=StrategyTypeEnum.MOMENTUM,
        parameters=MomentumParameters(
            lookback_period=20,
            momentum_threshold=0.02,
            instruments=['AAPL'],
            position_size=100,
        ),
    )

    update_data = {
        'name': 'Updated Momentum Strategy',
        'parameters': {
            'lookback_period': 30,
            'momentum_threshold': 0.03,
            'instruments': ['AAPL', 'MSFT', 'GOOGL'],
            'position_size': 150,
        },
        'risk_controls': {
            'max_position_size': str(Decimal('2000')),
            'max_portfolio_value': str(Decimal('75000')),
            'stop_loss_percent': str(Decimal('0.06')),
            'max_drawdown_percent': str(Decimal('0.15')),
            'daily_loss_limit': str(Decimal('1500')),
            'max_orders_per_day': 30,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{original_strategy.strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=update_data,
    ) as response:
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()

        strategy = TradingStrategyResponseSchema(**data)
        assert strategy.strategy_id == original_strategy.strategy_id
        assert strategy.name == update_data['name']
        assert strategy.parameters.lookback_period == update_data['parameters']['lookback_period']
        assert strategy.parameters.momentum_threshold == update_data['parameters']['momentum_threshold']
        assert strategy.updated_at is not None
        assert strategy.updated_at >= original_strategy.created_at


@pytest.mark.asyncio
async def test_put_strategy_partial_update(client, config, mock_auth, create_trading_strategy):
    """Test PUT /api/v1/strategies/{strategy_id} allows partial updates"""
    strategy = await create_trading_strategy()

    update_data = {'name': 'Partially Updated Strategy'}

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy.strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=update_data,
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        updated_strategy = TradingStrategyResponseSchema(**data)
        assert updated_strategy.name == update_data['name']
        assert updated_strategy.strategy_id == strategy.strategy_id


@pytest.mark.asyncio
async def test_put_strategy_validates_risk_controls(
        client, config, mongo_connection, mock_auth, create_trading_strategy,
):
    """Test PUT /api/v1/strategies/{strategy_id} validates risk control constraints"""
    strategy = await create_trading_strategy()

    update_data = {
        'risk_controls': {
            'max_position_size': '1000',
            'max_portfolio_value': '50000',
            'stop_loss_percent': '1.5',
            'max_drawdown_percent': '0.10',
            'daily_loss_limit': '1000',
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy.strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=update_data,
    ) as response:
        assert response.status == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = await response.json()
        assert 'title' in data
        assert data['status'] == 422
        assert 'invalid_params' in data


@pytest.mark.asyncio
async def test_put_strategy_not_found(client, config, mongo_connection, mock_auth):
    """Test PUT /api/v1/strategies/{strategy_id} returns 404 for non-existent strategy"""
    non_existent_id = uuid4()

    update_data = {'name': 'This Strategy Does Not Exist'}

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{non_existent_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=update_data,
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert 'detail' in data
        assert 'title' in data
        assert 'status' in data
        assert data['status'] == 404


@pytest.mark.asyncio
async def test_put_strategy_unauthorized_without_token(client, config, services):
    """Test PUT /api/v1/strategies/{strategy_id} requires authentication (401)"""
    strategy_id = uuid4()
    update_data = {'name': 'Unauthorized Update'}

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Content-Type': 'application/json'},
        json=update_data,
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401
        assert data['title'] == 'Unauthorized'


@pytest.mark.asyncio
async def test_put_strategy_bad_request_invalid_data(client, config, mongo_connection, mock_auth):
    """Test PUT /api/v1/strategies/{strategy_id} returns 422 for invalid data"""
    strategy_id = uuid4()

    invalid_data = {
        'name': '',
        'parameters': 'not-a-dict',
    }

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=invalid_data,
    ) as response:
        assert response.status == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = await response.json()
        assert 'invalid_params' in data
        assert 'title' in data
        assert data['status'] == 422


@pytest.mark.asyncio
async def test_put_strategy_updates_timestamp(client, config, mock_auth, create_trading_strategy):
    """Test PUT /api/v1/strategies/{strategy_id} updates the updated_at timestamp"""
    strategy = await create_trading_strategy()
    update_data = {'name': 'Timestamp Test Strategy'}

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy.strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=update_data,
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        strategy = TradingStrategyResponseSchema(**data)
        assert strategy.updated_at is not None
        assert strategy.created_at is not None
        assert strategy.updated_at >= strategy.created_at

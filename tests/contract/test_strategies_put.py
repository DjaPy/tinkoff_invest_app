"""
Contract test for PUT /api/v1/strategies/{strategy_id} endpoint (T007)

This test validates the API contract for updating trading strategies.
It should FAIL until the actual endpoint implementation is complete.

Following TDD approach - tests written before implementation.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field
from starlette import status

from src.algo_trading.adapters.models.strategy import RiskControls, TradingStrategyDocument


class UpdateStrategyRequest(BaseModel):
    """Request schema for PUT /api/v1/strategies/{strategy_id}."""

    name: str | None = Field(None, min_length=1, max_length=100, description='Strategy name')
    parameters: dict | None = Field(None, description='Strategy-specific parameters')
    risk_controls: RiskControls | None = Field(None, description='Risk management configuration')


@pytest.mark.asyncio
async def test_put_strategy_updates_existing_strategy(client, config, pydantic_generator_data):
    """Test PUT /api/v1/strategies/{strategy_id} updates an existing strategy"""
    strategy_id = uuid4()

    update_data = {
        'name': 'Updated Momentum Strategy',
        'parameters': {
            'lookback_period': 30,  # Changed from 20
            'momentum_threshold': 0.03,  # Changed from 0.02
            'instruments': ['AAPL', 'MSFT', 'GOOGL'],  # Added GOOGL
            'position_size': 150,  # Changed from 100
        },
        'risk_controls': {
            'max_position_size': Decimal('2000'),
            'max_portfolio_value': Decimal('75000'),
            'stop_loss_percent': Decimal('0.06'),
            'max_drawdown_percent': Decimal('0.15'),
            'daily_loss_limit': Decimal('1500'),
            'max_orders_per_day': 30,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    # Validate request structure
    UpdateStrategyRequest(**update_data)

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=update_data,
    ) as response:
        # Contract assertions
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()

        # Validate response using Pydantic model
        strategy = TradingStrategyDocument(**data)
        assert strategy.strategy_id == strategy_id
        assert strategy.name == update_data['name']
        assert strategy.parameters == update_data['parameters']
        assert strategy.updated_at is not None


@pytest.mark.asyncio
async def test_put_strategy_partial_update(client, config):
    """Test PUT /api/v1/strategies/{strategy_id} allows partial updates"""
    strategy_id = uuid4()

    # Only updating name
    update_data = {'name': 'Partially Updated Strategy'}

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=update_data,
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        strategy = TradingStrategyDocument(**data)
        assert strategy.name == update_data['name']
        # Other fields should remain unchanged


@pytest.mark.asyncio
async def test_put_strategy_validates_risk_controls(client, config):
    """Test PUT /api/v1/strategies/{strategy_id} validates risk control constraints"""
    strategy_id = uuid4()

    update_data = {
        'risk_controls': {
            'max_position_size': Decimal('1000'),
            'max_portfolio_value': Decimal('50000'),
            'stop_loss_percent': Decimal('1.5'),  # Invalid: > 1.0
            'max_drawdown_percent': Decimal('0.10'),
            'daily_loss_limit': Decimal('1000'),
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
            'enabled': True,
        },
    }

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=update_data,
    ) as response:
        # Should return validation error
        assert response.status == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = await response.json()
        assert 'type' in data
        assert 'title' in data
        assert data['status'] == 422
        assert 'invalid_params' in data


@pytest.mark.asyncio
async def test_put_strategy_not_found(client, config):
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
        # RFC7807 error format
        assert 'type' in data
        assert 'title' in data
        assert 'status' in data
        assert data['status'] == 404


@pytest.mark.asyncio
async def test_put_strategy_unauthorized_without_token(client, config):
    """Test PUT /api/v1/strategies/{strategy_id} requires authentication (401)"""
    strategy_id = uuid4()
    update_data = {'name': 'Unauthorized Update'}

    # No Authorization header
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
async def test_put_strategy_bad_request_invalid_data(client, config):
    """Test PUT /api/v1/strategies/{strategy_id} returns 400 for invalid data"""
    strategy_id = uuid4()

    # Invalid data structure
    invalid_data = {
        'name': '',  # Empty name violates min_length constraint
        'parameters': 'not-a-dict',  # Should be dict
    }

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=invalid_data,
    ) as response:
        assert response.status in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        data = await response.json()
        assert 'type' in data
        assert 'title' in data
        assert 'status' in data


@pytest.mark.asyncio
async def test_put_strategy_updates_timestamp(client, config):
    """Test PUT /api/v1/strategies/{strategy_id} updates the updated_at timestamp"""
    strategy_id = uuid4()
    update_data = {'name': 'Timestamp Test Strategy'}

    async with client.put(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=update_data,
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        strategy = TradingStrategyDocument(**data)
        # updated_at should be present and more recent than created_at
        assert strategy.updated_at is not None
        assert strategy.created_at is not None
        # In a real scenario, updated_at >= created_at

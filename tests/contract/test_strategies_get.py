"""
Contract test for GET /api/v1/strategies endpoint (T006)

This test validates the API contract for listing trading strategies.
It should FAIL until the actual endpoint implementation is complete.

Following TDD approach - tests written before implementation.
"""

import pytest
from pydantic import BaseModel, Field, ValidationError
from starlette import status

from src.algo_trading.adapters.models.strategy import StrategyStatus, StrategyType, TradingStrategy


class StrategyListResponse(BaseModel):
    """Response schema for GET /api/v1/strategies."""

    strategies: list[TradingStrategy] = Field(description='List of trading strategies')
    total: int = Field(ge=0, description='Total number of strategies')


@pytest.mark.asyncio
async def test_get_strategies_returns_strategy_list(client, config):
    """Test GET /api/v1/strategies returns list of strategies"""
    # This test is designed to FAIL until implementation
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        # Contract assertions based on trading_strategies_api.yaml
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()

        # Validate response structure using Pydantic model
        response_model = StrategyListResponse(**data)
        assert isinstance(response_model.strategies, list)
        assert isinstance(response_model.total, int)
        assert response_model.total >= 0


@pytest.mark.asyncio
async def test_get_strategies_validates_strategy_structure(client, config, pydantic_generator_data):
    """Test GET /api/v1/strategies returns strategies with correct Pydantic structure"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = StrategyListResponse(**data)

        # If strategies exist, validate each strategy against TradingStrategy model
        if response_model.strategies:
            for strategy in response_model.strategies:
                # Validate all required fields exist
                assert strategy.strategy_id is not None
                assert strategy.name is not None
                assert strategy.strategy_type in [
                    StrategyType.MOMENTUM,
                    StrategyType.MEAN_REVERSION,
                    StrategyType.ARBITRAGE,
                    StrategyType.MARKET_MAKING,
                ]
                assert strategy.status in [
                    StrategyStatus.INACTIVE,
                    StrategyStatus.ACTIVE,
                    StrategyStatus.PAUSED,
                    StrategyStatus.STOPPED,
                    StrategyStatus.ERROR,
                ]
                assert strategy.parameters is not None
                assert isinstance(strategy.parameters, dict)
                assert strategy.risk_controls is not None
                assert strategy.created_at is not None
                assert strategy.updated_at is not None
                assert strategy.created_by is not None


@pytest.mark.asyncio
async def test_get_strategies_empty_list_when_no_strategies(client, config, mongo_connection):
    """Test GET /api/v1/strategies returns empty list when no strategies"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = StrategyListResponse(**data)
        assert response_model.total == 0
        assert response_model.strategies == []


@pytest.mark.asyncio
async def test_get_strategies_unauthorized_without_token(client, config):
    """Test GET /api/v1/strategies requires authentication (401)"""
    # No Authorization header
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        # RFC7807 error format
        assert 'type' in data
        assert 'title' in data
        assert 'status' in data
        assert data['status'] == 401


@pytest.mark.asyncio
async def test_get_strategies_validates_pydantic_model(client, config, pydantic_generator_data):
    """Test GET /api/v1/strategies response validates against Pydantic model"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        # This should not raise ValidationError if response matches schema
        try:
            response_model = StrategyListResponse(**data)
            # Verify count matches
            assert len(response_model.strategies) == response_model.total
        except ValidationError as e:
            pytest.fail(f'Response validation failed: {e}')


@pytest.mark.asyncio
async def test_get_strategies_handles_internal_errors(client, config):
    """Test GET /api/v1/strategies handles internal server errors (500)"""
    # This will test error handling when implemented
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        # If there's an internal error, it should follow RFC7807 format
        if response.status == status.HTTP_500_INTERNAL_SERVER_ERROR:
            data = await response.json()
            assert 'type' in data
            assert 'title' in data
            assert 'status' in data
            assert data['status'] == 500

"""
Contract test for GET /api/v1/strategies endpoint (T006)

This test validates the API contract for listing trading strategies.
It should FAIL until the actual endpoint implementation is complete.

Following TDD approach - tests written before implementation.
"""

from pydantic import BaseModel, Field
from starlette import status

from src.algo_trading.ports.api.v1.schemas.strategies_schema import TradingStrategyResponseSchema
from src.algo_trading.adapters.models.strategy import StrategyStatusEnum, StrategyTypeEnum


class StrategyListResponse(BaseModel):
    """Response schema for GET /api/v1/strategies."""

    strategies: list[TradingStrategyResponseSchema] = Field(description='List of trading strategies')
    total: int = Field(ge=0, description='Total number of strategies')



async def test_get_strategies_returns_strategy_list(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/strategies returns list of strategies"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()
        response_model = StrategyListResponse(**data)
        assert isinstance(response_model.strategies, list)
        assert isinstance(response_model.total, int)
        assert response_model.total >= 0



async def test_get_strategies_validates_strategy_structure(
    client,
    config,
    mongo_connection,
    mock_auth,
    pydantic_generator_data,
):
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
                    StrategyTypeEnum.MOMENTUM,
                    StrategyTypeEnum.MEAN_REVERSION,
                    StrategyTypeEnum.ARBITRAGE,
                    StrategyTypeEnum.MARKET_MAKING,
                ]
                assert strategy.status in [
                    StrategyStatusEnum.INACTIVE,
                    StrategyStatusEnum.ACTIVE,
                    StrategyStatusEnum.PAUSED,
                    StrategyStatusEnum.STOPPED,
                    StrategyStatusEnum.ERROR,
                ]
                assert strategy.parameters is not None
                assert isinstance(strategy.parameters, dict)
                assert strategy.risk_controls is not None
                assert strategy.created_at is not None
                assert strategy.updated_at is not None
                assert strategy.created_by is not None



async def test_get_strategies_empty_list_when_no_strategies(client, config, services, mock_auth, mongo_connection):
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



async def test_get_strategies_unauthorized_without_token(client, config):
    """Test GET /api/v1/strategies requires authentication (401)"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert 'detail' in data
        assert 'title' in data
        assert 'status' in data
        assert data['status'] == 401



async def test_get_strategies_validates_pydantic_model(
        client, config, mongo_connection, mock_auth, create_trading_strategy,
):
    """Test GET /api/v1/strategies response validates against Pydantic model"""

    user_id = mock_auth
    strategy = await create_trading_strategy(created_by=user_id)

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = StrategyListResponse(**data)
        assert len(response_model.strategies) == response_model.total
        assert response_model.strategies[0].strategy_id == strategy.strategy_id
        assert response_model.strategies[0].name == strategy.name
        assert response_model.strategies[0].strategy_type == strategy.strategy_type
        assert response_model.strategies[0].status == strategy.status


async def test_get_strategies_handles_internal_errors(client, config, mock_auth):
    """Test GET /api/v1/strategies handles internal server errors (500)"""
    # This will test error handling when implemented
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        if response.status == status.HTTP_500_INTERNAL_SERVER_ERROR:
            data = await response.json()
            assert 'detail' in data
            assert 'title' in data
            assert 'status' in data
            assert data['status'] == 500

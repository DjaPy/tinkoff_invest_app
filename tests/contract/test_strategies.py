"""
Contract tests for /api/v1/strategies endpoints

These tests validate the API contract for managing trading strategies.
Following the pattern from test_orders.py and test_positions.py
"""
import uuid
from decimal import Decimal

from starlette import status

from src.algo_trading.adapters.models.strategy import (
    MeanReversionParameters,
    MomentumParameters,
    StrategyTypeEnum,
)


async def test_get_strategies_returns_strategy_list(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/strategies returns list of strategies (T039)"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        # Validate response structure
        assert 'strategies' in data
        assert 'total' in data
        assert isinstance(data['strategies'], list)
        assert isinstance(data['total'], int)


async def test_get_strategies_validates_strategy_structure(
        client,
        config,
        mongo_connection,
        create_risk_controls,
        create_trading_strategy,
        mock_auth,
):
    """Test GET /api/v1/strategies validates strategy structure (T040)"""
    user_id = mock_auth
    risk_controls = create_risk_controls(max_position_size=10000.0, max_portfolio_value=50000.0, stop_loss_percent=0.02)
    strategy = await create_trading_strategy(
        risk_controls=risk_controls,
        name='Test Momentum Strategy',
        strategy_type=StrategyTypeEnum.MOMENTUM,
        parameters=MomentumParameters(
            lookback_period=20,
            momentum_threshold=0.02,
            instruments=['AAPL', 'MSFT'],
            position_size=100,
        ),
        instruments=['AAPL', 'MSFT'],
        created_by=user_id,
    )

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        assert data['total'] >= 1

        if data['strategies']:
            strategy_data = data['strategies'][0]
            assert 'strategy_id' in strategy_data
            assert 'name' in strategy_data
            assert 'strategy_type' in strategy_data
            assert 'status' in strategy_data
            assert 'created_at' in strategy_data
            assert 'updated_at' in strategy_data

    # Cleanup
    await strategy.delete()


async def test_get_strategies_empty_list_when_no_strategies(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/strategies returns empty list (T041)"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        assert data['total'] == 0
        assert data['strategies'] == []


async def test_get_strategies_unauthorized_without_token(client, config, mongo_connection):
    """Test GET /api/v1/strategies requires authentication (T042)"""
    async with client.get(url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies') as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()

        assert data['status'] == 401
        assert 'title' in data


async def test_get_strategies_validates_pydantic_model(
    client,
    config,
    pydantic_generator_data,
    create_risk_controls,
    create_trading_strategy,
    mock_auth,
):

    risk_controls =  create_risk_controls(
        max_position_size=Decimal('10000.0'),
        max_portfolio_value=Decimal('25000.0'),
        stop_loss_percent=Decimal('0.03'),
    )
    await create_trading_strategy(
        name='Pydantic Test Strategy',
        strategy_type=StrategyTypeEnum.MEAN_REVERSION,
        parameters=MeanReversionParameters(
            moving_average_period=50,
            std_dev_threshold=2.0,
            instruments=['AAPL', 'MSFT'],
        ),
        risk_controls=risk_controls,
        created_by=uuid.uuid4(),
    )

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        if data['strategies']:
            for strategy_data in data['strategies']:
                assert strategy_data['name']
                assert strategy_data['strategy_type'] is not None


async def test_get_strategies_handles_internal_errors(client, config, services, mock_auth):
    """Test GET /api/v1/strategies handles internal errors gracefully (T044)"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        if response.status == status.HTTP_500_INTERNAL_SERVER_ERROR:
            data = await response.json()
            assert 'detail' in data
            assert data['status'] == 500

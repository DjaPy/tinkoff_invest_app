"""
Contract tests for strategy lifecycle endpoints (T009, T010, T011)

POST /api/v1/strategies/{strategy_id}/start - Start strategy (T009)
POST /api/v1/strategies/{strategy_id}/stop - Stop strategy (T010)
POST /api/v1/strategies/{strategy_id}/pause - Pause strategy (T011)

These tests validate the API contracts for managing strategy execution state.
They should FAIL until the actual endpoint implementations are complete.

Following TDD approach - tests written before implementation.
"""

from uuid import uuid4

import pytest
from starlette import status

from src.algo_trading.adapters.models.strategy import StrategyStatusEnum, TradingStrategyDocument
from src.algo_trading.adapters.models.position import PortfolioPositionDocument

@pytest.mark.asyncio
async def test_start_strategy_activates_inactive_strategy(client, config, mock_auth, create_trading_strategy):
    """Test POST /api/v1/strategies/{strategy_id}/start activates a strategy"""
    strategy = await create_trading_strategy(status=StrategyStatusEnum.INACTIVE)

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy.strategy_id}/start',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()
        strategy = TradingStrategyDocument(**data)
        assert strategy.strategy_id == strategy.strategy_id
        assert strategy.status == StrategyStatusEnum.ACTIVE
        assert strategy.updated_at is not None


@pytest.mark.asyncio
async def test_start_strategy_not_found(client, config, mongo_connection, mock_auth):
    """Test POST /api/v1/strategies/{strategy_id}/start returns 404 for non-existent strategy"""
    non_existent_id = uuid4()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{non_existent_id}/start',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert 'detail' in data
        assert 'status' in data
        assert data['status'] == 404


@pytest.mark.asyncio
async def test_start_strategy_conflict_invalid_state(client, config, mongo_connection, mock_auth):
    """Test POST /api/v1/strategies/{strategy_id}/start returns 409 for invalid state transition"""
    strategy_id = uuid4()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        if response.status == status.HTTP_409_CONFLICT:
            data = await response.json()
            assert 'detail' in data
            assert 'title' in data
            assert 'status' in data
            assert data['status'] == 409


@pytest.mark.asyncio
async def test_start_strategy_unauthorized(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/start requires authentication"""
    strategy_id = uuid4()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401


@pytest.mark.asyncio
async def test_stop_strategy_halts_active_strategy(client, config, mongo_connection, mock_auth, create_trading_strategy):
    """Test POST /api/v1/strategies/{strategy_id}/stop halts a running strategy"""
    strategy = await create_trading_strategy(status=StrategyStatusEnum.ACTIVE)

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy.strategy_id}/stop',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()
        strategy = TradingStrategyDocument(**data)
        assert strategy.strategy_id == strategy.strategy_id
        assert strategy.status == StrategyStatusEnum.STOPPED
        assert strategy.updated_at is not None


@pytest.mark.asyncio
async def test_stop_strategy_closes_positions(client, config, mongo_connection, mock_auth, create_trading_strategy):
    """Test POST /api/v1/strategies/{strategy_id}/stop closes all open positions"""
    strategy = await create_trading_strategy(status=StrategyStatusEnum.ACTIVE)

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy.strategy_id}/stop',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        strategy = TradingStrategyDocument(**data)
        assert strategy.status == StrategyStatusEnum.STOPPED


@pytest.mark.asyncio
async def test_stop_strategy_not_found(client, config, mongo_connection, mock_auth):
    """Test POST /api/v1/strategies/{strategy_id}/stop returns 404 for non-existent strategy"""
    non_existent_id = uuid4()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{non_existent_id}/stop',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert data['status'] == 404


@pytest.mark.asyncio
async def test_stop_strategy_unauthorized(client, config, services):
    """Test POST /api/v1/strategies/{strategy_id}/stop requires authentication"""
    strategy_id = uuid4()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/stop',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401


@pytest.mark.asyncio
async def test_pause_strategy_temporarily_halts_execution(client, config, mock_auth, create_trading_strategy):
    """Test POST /api/v1/strategies/{strategy_id}/pause temporarily halts strategy"""
    strategy = await create_trading_strategy(status=StrategyStatusEnum.ACTIVE)

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy.strategy_id}/pause',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()

        strategy = TradingStrategyDocument(**data)
        assert strategy.strategy_id == strategy.strategy_id
        assert strategy.status == StrategyStatusEnum.PAUSED
        assert strategy.updated_at is not None


@pytest.mark.asyncio
async def test_pause_strategy_keeps_positions_open(
    client,
    config,
    mongo_connection,
    mock_auth,
    create_trading_strategy,
    create_position,
):
    """Test POST /api/v1/strategies/{strategy_id}/pause keeps positions open"""
    strategy = await create_trading_strategy(status=StrategyStatusEnum.ACTIVE)

    position1 = await create_position(strategy_id=strategy.strategy_id, instrument='AAPL')
    position2 = await create_position(strategy_id=strategy.strategy_id, instrument='MSFT')

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy.strategy_id}/pause',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        paused_strategy = TradingStrategyDocument(**data)
        assert paused_strategy.status == StrategyStatusEnum.PAUSED


        positions = await PortfolioPositionDocument.find(
            PortfolioPositionDocument.strategy_id == strategy.strategy_id
        ).to_list()
    
        assert len(positions) == 2
        assert position1.position_id in {p.position_id for p in positions}
        assert position2.position_id in {p.position_id for p in positions}


@pytest.mark.asyncio
async def test_pause_strategy_not_found(client, config, mongo_connection, mock_auth):
    """Test POST /api/v1/strategies/{strategy_id}/pause returns 404 for non-existent strategy"""
    non_existent_id = uuid4()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{non_existent_id}/pause',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert data['status'] == 404


@pytest.mark.asyncio
async def test_pause_strategy_unauthorized(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/pause requires authentication"""
    strategy_id = uuid4()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/pause',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401


@pytest.mark.parametrize(
    'action,expected_status',
    [
        ('start', StrategyStatusEnum.ACTIVE),
        ('stop', StrategyStatusEnum.STOPPED),
        ('pause', StrategyStatusEnum.PAUSED),
    ],
)
@pytest.mark.asyncio
async def test_lifecycle_actions_update_status_correctly(client, config, action, expected_status):
    """Test all lifecycle actions update strategy status correctly"""
    strategy_id = uuid4()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/{action}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        if response.status == status.HTTP_200_OK:
            data = await response.json()
            strategy = TradingStrategyDocument(**data)
            assert strategy.status == expected_status

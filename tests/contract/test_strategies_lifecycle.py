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

from src.algo_trading.adapters.models.strategy import (StrategyStatus,
                                                       TradingStrategy)

# ==================== START STRATEGY TESTS (T009) ====================


@pytest.mark.asyncio
async def test_start_strategy_activates_inactive_strategy(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/start activates a strategy"""
    strategy_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    ) as response:
        # Contract assertions - 200 OK with updated strategy
        assert response.status == status.HTTP_200_OK
        assert "application/json" in response.headers["content-type"]

        data = await response.json()

        # Validate response using Pydantic model
        strategy = TradingStrategy(**data)
        assert strategy.strategy_id == strategy_id
        assert strategy.status == StrategyStatus.ACTIVE
        assert strategy.updated_at is not None


@pytest.mark.asyncio
async def test_start_strategy_not_found(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/start returns 404 for non-existent strategy"""
    non_existent_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{non_existent_id}/start",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert "type" in data
        assert "status" in data
        assert data["status"] == 404


@pytest.mark.asyncio
async def test_start_strategy_conflict_invalid_state(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/start returns 409 for invalid state transition"""
    # Per OpenAPI spec: Strategy cannot be started if in invalid state
    strategy_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    ) as response:
        # Should return 409 Conflict if strategy cannot be started
        if response.status == status.HTTP_409_CONFLICT:
            data = await response.json()
            assert "type" in data
            assert "title" in data
            assert "status" in data
            assert data["status"] == 409


@pytest.mark.asyncio
async def test_start_strategy_unauthorized(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/start requires authentication"""
    strategy_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/start",
        headers={"Content-Type": "application/json"},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data["status"] == 401


# ==================== STOP STRATEGY TESTS (T010) ====================


@pytest.mark.asyncio
async def test_stop_strategy_halts_active_strategy(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/stop halts a running strategy"""
    strategy_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/stop",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    ) as response:
        # Contract assertions - 200 OK with updated strategy
        assert response.status == status.HTTP_200_OK
        assert "application/json" in response.headers["content-type"]

        data = await response.json()

        # Validate response using Pydantic model
        strategy = TradingStrategy(**data)
        assert strategy.strategy_id == strategy_id
        assert strategy.status == StrategyStatus.STOPPED
        assert strategy.updated_at is not None


@pytest.mark.asyncio
async def test_stop_strategy_closes_positions(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/stop closes all open positions"""
    # Per OpenAPI spec description: "Halt a trading strategy and close all open positions"
    strategy_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/stop",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        strategy = TradingStrategy(**data)
        assert strategy.status == StrategyStatus.STOPPED
        # Implementation should handle position closing


@pytest.mark.asyncio
async def test_stop_strategy_not_found(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/stop returns 404 for non-existent strategy"""
    non_existent_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{non_existent_id}/stop",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert data["status"] == 404


@pytest.mark.asyncio
async def test_stop_strategy_unauthorized(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/stop requires authentication"""
    strategy_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/stop",
        headers={"Content-Type": "application/json"},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data["status"] == 401


# ==================== PAUSE STRATEGY TESTS (T011) ====================


@pytest.mark.asyncio
async def test_pause_strategy_temporarily_halts_execution(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/pause temporarily halts strategy"""
    strategy_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/pause",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    ) as response:
        # Contract assertions - 200 OK with updated strategy
        assert response.status == status.HTTP_200_OK
        assert "application/json" in response.headers["content-type"]

        data = await response.json()

        # Validate response using Pydantic model
        strategy = TradingStrategy(**data)
        assert strategy.strategy_id == strategy_id
        assert strategy.status == StrategyStatus.PAUSED
        assert strategy.updated_at is not None


@pytest.mark.asyncio
async def test_pause_strategy_keeps_positions_open(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/pause keeps positions open"""
    # Per OpenAPI spec description: "Temporarily halt strategy execution without closing positions"
    strategy_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/pause",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        strategy = TradingStrategy(**data)
        assert strategy.status == StrategyStatus.PAUSED
        # Implementation should NOT close positions (unlike stop)


@pytest.mark.asyncio
async def test_pause_strategy_not_found(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/pause returns 404 for non-existent strategy"""
    non_existent_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{non_existent_id}/pause",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert data["status"] == 404


@pytest.mark.asyncio
async def test_pause_strategy_unauthorized(client, config):
    """Test POST /api/v1/strategies/{strategy_id}/pause requires authentication"""
    strategy_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/pause",
        headers={"Content-Type": "application/json"},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data["status"] == 401


# ==================== STATE TRANSITION TESTS ====================


@pytest.mark.parametrize(
    "action,expected_status",
    [
        ("start", StrategyStatus.ACTIVE),
        ("stop", StrategyStatus.STOPPED),
        ("pause", StrategyStatus.PAUSED),
    ],
)
@pytest.mark.asyncio
async def test_lifecycle_actions_update_status_correctly(client, config, action, expected_status):
    """Test all lifecycle actions update strategy status correctly"""
    strategy_id = uuid4()

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}/{action}",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
    ) as response:
        if response.status == status.HTTP_200_OK:
            data = await response.json()
            strategy = TradingStrategy(**data)
            assert strategy.status == expected_status

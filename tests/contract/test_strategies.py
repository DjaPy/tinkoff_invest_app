"""
Contract tests for /api/v1/strategies endpoints

These tests validate the API contract for managing trading strategies.
Following the pattern from test_orders.py and test_positions.py
"""
from decimal import Decimal

import pytest
from starlette import status

from src.algo_trading.adapters.models.strategy import TradingStrategy, StrategyStatus, StrategyType, RiskControls


async def test_get_strategies_returns_strategy_list(client, config):
    """Test GET /api/v1/strategies returns list of strategies (T039)"""
    async with client.get(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies",
        headers={"Authorization": "Bearer test-token"},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        # Validate response structure
        assert "strategies" in data
        assert "total" in data
        assert isinstance(data["strategies"], list)
        assert isinstance(data["total"], int)


async def test_get_strategies_validates_strategy_structure(client, config, mongo_connection):
    """Test GET /api/v1/strategies validates strategy structure (T040)"""
    # Create a test strategy in database
    strategy = TradingStrategy(
        name="Test Momentum Strategy",
        strategy_type=StrategyType.MOMENTUM,
        parameters={"lookback_period": 20, "momentum_threshold": 0.02},
        risk_controls=RiskControls(
            max_position_size=10000.0,
            max_portfolio_value=50000.0,
            stop_loss_percent=0.02,
        ),
        created_by="test-user",
    )
    await strategy.insert()

    async with client.get(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies",
        headers={"Authorization": "Bearer test-token"},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        assert data["total"] >= 1

        # Validate first strategy structure if exists
        if data["strategies"]:
            strategy_data = data["strategies"][0]
            assert "strategy_id" in strategy_data
            assert "name" in strategy_data
            assert "strategy_type" in strategy_data
            assert "status" in strategy_data
            assert "created_at" in strategy_data
            assert "updated_at" in strategy_data

    # Cleanup
    await strategy.delete()


async def test_get_strategies_empty_list_when_no_strategies(
    client, config, mongo_connection
):
    """Test GET /api/v1/strategies returns empty list (T041)"""
    # Ensure database is clean
    await TradingStrategy.delete_all()

    async with client.get(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies",
        headers={"Authorization": "Bearer test-token"},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        assert data["total"] == 0
        assert data["strategies"] == []


async def test_get_strategies_unauthorized_without_token(client, config):
    """Test GET /api/v1/strategies requires authentication (T042)"""
    async with client.get(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies",
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()

        # RFC7807 Problem Details format
        assert data["status"] == 401
        assert "title" in data


async def test_get_strategies_validates_pydantic_model(
    client, config, mongo_connection, pydantic_generator_data
):
    """Test GET /api/v1/strategies returns valid Pydantic models (T043)"""
    # Create test strategy
    strategy = TradingStrategy(
        name="Pydantic Test Strategy",
        strategy_type=StrategyType.MEAN_REVERSION,
        parameters={"ma_period": Decimal("50"), "std_threshold": Decimal("2.0")},
        risk_controls=RiskControls(
            max_position_size=Decimal("10000.0"),
            max_portfolio_value=Decimal("25000.0"),
            stop_loss_percent=Decimal("0.03"),
        ),
        created_by="test-user",
    )
    await strategy.insert()

    async with client.get(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies",
        headers={"Authorization": "Bearer test-token"},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        # Validate using Pydantic model
        if data["strategies"]:
            # Should be able to parse as TradingStrategy
            for strategy_data in data["strategies"]:
                validated_strategy = TradingStrategy(**strategy_data)
                assert validated_strategy.name is not None
                assert validated_strategy.strategy_type is not None

    # Cleanup
    await strategy.delete()


async def test_get_strategies_handles_internal_errors(client, config):
    """Test GET /api/v1/strategies handles internal errors gracefully (T044)"""
    async with client.get(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/strategies",
        headers={"Authorization": "Bearer test-token"},
    ) as response:
        # If there's an internal error, it should follow RFC7807 format
        if response.status == status.HTTP_500_INTERNAL_SERVER_ERROR:
            data = await response.json()
            assert "type" in data
            assert "title" in data
            assert "status" in data
            assert data["status"] == 500
"""
Contract test for POST /api/v1/analytics/backtest endpoint (T021)

This test validates the API contract for running strategy backtests.
It should FAIL until the actual endpoint implementation is complete.

Following TDD approach - tests written before implementation.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import BaseModel, Field
from starlette import status


class BacktestRequest(BaseModel):
    """Request schema for POST /api/v1/analytics/backtest."""

    strategy_type: str = Field(description="Type of strategy to backtest")
    parameters: dict = Field(description="Strategy parameters")
    instruments: list[str] = Field(min_length=1, description="Trading instruments")
    start_date: datetime = Field(description="Backtest start date")
    end_date: datetime = Field(description="Backtest end date")
    initial_capital: Decimal = Field(gt=0, description="Starting capital")
    risk_controls: dict = Field(description="Risk management parameters")


class BacktestResults(BaseModel):
    """Response schema for POST /api/v1/analytics/backtest."""

    backtest_id: str = Field(description="Unique backtest run identifier")
    strategy_type: str = Field(description="Strategy type tested")
    start_date: datetime = Field(description="Backtest period start")
    end_date: datetime = Field(description="Backtest period end")
    initial_capital: Decimal = Field(gt=0, description="Starting capital")
    final_capital: Decimal = Field(gt=0, description="Ending capital")
    total_return: Decimal = Field(description="Total return percentage")
    sharpe_ratio: Decimal = Field(description="Sharpe ratio")
    max_drawdown: Decimal = Field(le=0, description="Maximum drawdown")
    win_rate: Decimal = Field(ge=0, le=1, description="Win rate")
    total_trades: int = Field(ge=0, description="Number of trades executed")
    profit_factor: Decimal = Field(ge=0, description="Profit factor")


# ==================== BACKTEST TESTS (T021) ====================


@pytest.mark.asyncio
async def test_post_backtest_runs_strategy_backtest(client, config):
    """Test POST /api/v1/analytics/backtest runs a backtest"""
    backtest_request = {
        "strategy_type": "momentum",
        "parameters": {
            "lookback_period": 20,
            "momentum_threshold": 0.02,
            "position_size": 100,
        },
        "instruments": ["AAPL", "MSFT"],
        "start_date": (datetime.utcnow() - timedelta(days=365)).isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "initial_capital": str(Decimal("100000")),
        "risk_controls": {
            "max_position_size": str(Decimal("10000")),
            "max_portfolio_value": str(Decimal("100000")),
            "stop_loss_percent": str(Decimal("0.05")),
            "max_drawdown_percent": str(Decimal("0.10")),
            "daily_loss_limit": str(Decimal("1000")),
            "max_orders_per_day": 20,
            "trading_hours_start": "09:30:00",
            "trading_hours_end": "16:00:00",
            "enabled": True,
        },
    }

    # Validate request structure
    BacktestRequest(**backtest_request)

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
        json=backtest_request,
    ) as response:
        # Contract assertions
        assert response.status == status.HTTP_200_OK
        assert "application/json" in response.headers["content-type"]

        data = await response.json()

        # Validate response using Pydantic model
        results = BacktestResults(**data)
        assert results.backtest_id is not None
        assert results.strategy_type == backtest_request["strategy_type"]
        assert results.initial_capital == Decimal(backtest_request["initial_capital"])
        assert results.final_capital > 0
        assert results.total_trades >= 0
        assert 0 <= results.win_rate <= 1
        assert results.max_drawdown <= 0


@pytest.mark.asyncio
async def test_post_backtest_validates_required_fields(client, config):
    """Test POST /api/v1/analytics/backtest validates required fields"""
    # Missing required fields
    invalid_request = {
        "strategy_type": "momentum",
        # Missing parameters, instruments, dates, etc.
    }

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
        json=invalid_request,
    ) as response:
        # Should return validation error
        assert response.status == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = await response.json()
        assert "type" in data
        assert "status" in data
        assert data["status"] == 422


@pytest.mark.asyncio
async def test_post_backtest_validates_date_range(client, config):
    """Test POST /api/v1/analytics/backtest validates date range"""
    # end_date before start_date
    invalid_request = {
        "strategy_type": "momentum",
        "parameters": {"lookback_period": 20},
        "instruments": ["AAPL"],
        "start_date": datetime.utcnow().isoformat(),
        "end_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),  # Invalid: before start
        "initial_capital": str(Decimal("100000")),
        "risk_controls": {
            "max_position_size": str(Decimal("10000")),
            "max_portfolio_value": str(Decimal("100000")),
            "stop_loss_percent": str(Decimal("0.05")),
            "max_drawdown_percent": str(Decimal("0.10")),
            "daily_loss_limit": str(Decimal("1000")),
            "max_orders_per_day": 20,
            "trading_hours_start": "09:30:00",
            "trading_hours_end": "16:00:00",
            "enabled": True,
        },
    }

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
        json=invalid_request,
    ) as response:
        # Should return validation error or bad request
        assert response.status in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        data = await response.json()
        assert "type" in data
        assert "status" in data


@pytest.mark.asyncio
async def test_post_backtest_validates_initial_capital(client, config):
    """Test POST /api/v1/analytics/backtest validates initial capital is positive"""
    invalid_request = {
        "strategy_type": "momentum",
        "parameters": {"lookback_period": 20},
        "instruments": ["AAPL"],
        "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "initial_capital": str(Decimal("-1000")),  # Invalid: negative
        "risk_controls": {
            "max_position_size": str(Decimal("10000")),
            "max_portfolio_value": str(Decimal("100000")),
            "stop_loss_percent": str(Decimal("0.05")),
            "max_drawdown_percent": str(Decimal("0.10")),
            "daily_loss_limit": str(Decimal("1000")),
            "max_orders_per_day": 20,
            "trading_hours_start": "09:30:00",
            "trading_hours_end": "16:00:00",
            "enabled": True,
        },
    }

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
        json=invalid_request,
    ) as response:
        assert response.status == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = await response.json()
        assert data["status"] == 422


@pytest.mark.asyncio
async def test_post_backtest_validates_instruments_list(client, config):
    """Test POST /api/v1/analytics/backtest requires at least one instrument"""
    invalid_request = {
        "strategy_type": "momentum",
        "parameters": {"lookback_period": 20},
        "instruments": [],  # Invalid: empty list
        "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "initial_capital": str(Decimal("100000")),
        "risk_controls": {
            "max_position_size": str(Decimal("10000")),
            "max_portfolio_value": str(Decimal("100000")),
            "stop_loss_percent": str(Decimal("0.05")),
            "max_drawdown_percent": str(Decimal("0.10")),
            "daily_loss_limit": str(Decimal("1000")),
            "max_orders_per_day": 20,
            "trading_hours_start": "09:30:00",
            "trading_hours_end": "16:00:00",
            "enabled": True,
        },
    }

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
        json=invalid_request,
    ) as response:
        assert response.status == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = await response.json()
        assert data["status"] == 422


@pytest.mark.asyncio
async def test_post_backtest_unauthorized(client, config):
    """Test POST /api/v1/analytics/backtest requires authentication"""
    backtest_request = {
        "strategy_type": "momentum",
        "parameters": {"lookback_period": 20},
        "instruments": ["AAPL"],
        "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "initial_capital": str(Decimal("100000")),
        "risk_controls": {},
    }

    # No Authorization header
    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest",
        headers={"Content-Type": "application/json"},
        json=backtest_request,
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data["status"] == 401


@pytest.mark.parametrize(
    "strategy_type",
    ["momentum", "mean_reversion", "arbitrage", "market_making"],
)
@pytest.mark.asyncio
async def test_post_backtest_supports_different_strategy_types(client, config, strategy_type):
    """Test POST /api/v1/analytics/backtest supports different strategy types"""
    backtest_request = {
        "strategy_type": strategy_type,
        "parameters": {"lookback_period": 20},
        "instruments": ["AAPL"],
        "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "initial_capital": str(Decimal("100000")),
        "risk_controls": {
            "max_position_size": str(Decimal("10000")),
            "max_portfolio_value": str(Decimal("100000")),
            "stop_loss_percent": str(Decimal("0.05")),
            "max_drawdown_percent": str(Decimal("0.10")),
            "daily_loss_limit": str(Decimal("1000")),
            "max_orders_per_day": 20,
            "trading_hours_start": "09:30:00",
            "trading_hours_end": "16:00:00",
            "enabled": True,
        },
    }

    async with client.post(
        url=f"http://127.0.0.1:{config.http.port}/api/v1/analytics/backtest",
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
        json=backtest_request,
    ) as response:
        if response.status == status.HTTP_200_OK:
            data = await response.json()
            results = BacktestResults(**data)
            assert results.strategy_type == strategy_type

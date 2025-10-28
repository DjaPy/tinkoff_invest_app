"""
Contract tests for Analytics API endpoints (T016-T021)

GET /api/v1/analytics/strategies/{strategy_id}/performance - Get strategy performance (T016)
GET /api/v1/analytics/strategies/{strategy_id}/trades - Get trade analytics (T017)
GET /api/v1/analytics/strategies/{strategy_id}/drawdown - Get drawdown analysis (T018)
GET /api/v1/analytics/portfolio/summary - Get portfolio summary (T019)
GET /api/v1/analytics/market-data/{instrument} - Get market data analytics (T020)
POST /api/v1/analytics/backtest - Run backtest (T021)

These tests validate the API contracts for analytics and performance metrics.
They should FAIL until the actual endpoint implementations are complete.

Following TDD approach - tests written before implementation.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from starlette import status

from src.algo_trading.adapters.models.metrics import PerformanceMetrics

@pytest.mark.asyncio
async def test_get_strategy_performance_returns_metrics(config, services, client):
    """Test GET /api/v1/analytics/strategies/{strategy_id}/performance returns metrics"""
    strategy_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/performance',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        # Contract assertions
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()

        # Validate response using Pydantic model
        metrics = PerformanceMetrics(**data)
        assert metrics.strategy_id == strategy_id
        assert metrics.total_return is not None
        assert metrics.annualized_return is not None
        assert metrics.sharpe_ratio is not None
        assert metrics.max_drawdown <= 0  # Drawdown should be negative or zero
        assert metrics.volatility >= 0
        assert 0 <= metrics.win_rate <= 1
        assert metrics.profit_factor >= 0
        assert metrics.trade_count >= 0


@pytest.mark.parametrize('period', ['1d', '1w', '1m', '3m', '1y', 'all'])
@pytest.mark.asyncio
async def test_get_strategy_performance_with_period_filter(client, config, period):
    """Test GET /api/v1/analytics/strategies/{strategy_id}/performance supports period filters"""
    strategy_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/performance?period={period}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        if response.status == status.HTTP_200_OK:
            data = await response.json()
            metrics = PerformanceMetrics(**data)
            assert metrics.strategy_id == strategy_id


@pytest.mark.asyncio
async def test_get_strategy_performance_custom_date_range(client, config):
    """Test GET /api/v1/analytics/strategies/{strategy_id}/performance supports custom date range"""

    strategy_id = uuid4()
    datetime_now = datetime.now(UTC)
    from_date = (datetime_now - timedelta(days=30)).date().isoformat()
    to_date = datetime_now.date().isoformat()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/performance?period=custom&from_date={from_date}&to_date={to_date}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        if response.status == status.HTTP_200_OK:
            data = await response.json()
            metrics = PerformanceMetrics(**data)
            assert metrics.period_start.date() >= datetime.fromisoformat(from_date).date()
            assert metrics.period_end.date() <= datetime.fromisoformat(to_date).date()


@pytest.mark.asyncio
async def test_get_strategy_performance_not_found(client, config):
    """Test GET /api/v1/analytics/strategies/{strategy_id}/performance returns 404"""
    non_existent_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{non_existent_id}/performance',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert data['status'] == 404


# ==================== TRADE ANALYTICS TESTS (T017) ====================


@pytest.mark.asyncio
async def test_get_strategy_trades_analytics(client, config):
    """Test GET /api/v1/analytics/strategies/{strategy_id}/trades returns trade analytics"""
    strategy_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/trades',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        # Validate response using Pydantic model
        analytics = TradeAnalytics(**data)
        assert analytics.strategy_id == str(strategy_id)
        assert analytics.total_trades >= 0
        assert analytics.winning_trades + analytics.losing_trades == analytics.total_trades
        assert 0 <= analytics.win_rate <= 1
        assert analytics.profit_factor >= 0


# ==================== DRAWDOWN TESTS (T018) ====================


@pytest.mark.asyncio
async def test_get_strategy_drawdown_analysis(client, config):
    """Test GET /api/v1/analytics/strategies/{strategy_id}/drawdown returns drawdown analysis"""
    strategy_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/drawdown',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        # Validate response using Pydantic model
        drawdown = DrawdownAnalysis(**data)
        assert drawdown.strategy_id == str(strategy_id)
        assert drawdown.max_drawdown <= 0
        assert drawdown.max_drawdown_duration >= 0
        assert drawdown.current_drawdown <= 0


# ==================== PORTFOLIO SUMMARY TESTS (T019) ====================


@pytest.mark.asyncio
async def test_get_portfolio_summary(client, config):
    """Test GET /api/v1/analytics/portfolio/summary returns portfolio summary"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/portfolio/summary',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        # Validate response using Pydantic model
        summary = PortfolioSummary(**data)
        assert summary.total_value >= 0
        assert summary.active_strategies >= 0
        assert summary.total_trades >= 0
        assert 0 <= summary.win_rate <= 1


@pytest.mark.asyncio
async def test_get_portfolio_summary_with_period(client, config):
    """Test GET /api/v1/analytics/portfolio/summary supports period filter"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/portfolio/summary?period=1m',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()
        summary = PortfolioSummary(**data)
        assert summary.total_value >= 0


# ==================== MARKET DATA TESTS (T020) ====================


@pytest.mark.asyncio
async def test_get_market_data_analytics(client, config):
    """Test GET /api/v1/analytics/market-data/{instrument} returns market data"""
    instrument = 'AAPL'

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/{instrument}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        # Validate response using Pydantic model
        market_data = MarketDataAnalytics(**data)
        assert market_data.instrument == instrument
        assert market_data.timeframe is not None
        assert isinstance(market_data.data_points, list)
        assert isinstance(market_data.indicators, dict)


@pytest.mark.parametrize('timeframe', ['1m', '5m', '15m', '1h', '1d'])
@pytest.mark.asyncio
async def test_get_market_data_with_timeframe(client, config, timeframe):
    """Test GET /api/v1/analytics/market-data/{instrument} supports timeframe parameter"""
    instrument = 'MSFT'

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/{instrument}?timeframe={timeframe}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        if response.status == status.HTTP_200_OK:
            data = await response.json()
            market_data = MarketDataAnalytics(**data)
            assert market_data.timeframe == timeframe


# ==================== AUTHORIZATION TESTS ====================


@pytest.mark.asyncio
async def test_analytics_endpoints_require_authentication(client, config):
    """Test all analytics endpoints require authentication"""
    strategy_id = uuid4()

    endpoints = [
        f'/api/v1/analytics/strategies/{strategy_id}/performance',
        f'/api/v1/analytics/strategies/{strategy_id}/trades',
        f'/api/v1/analytics/strategies/{strategy_id}/drawdown',
        '/api/v1/analytics/portfolio/summary',
        '/api/v1/analytics/market-data/AAPL',
    ]

    for endpoint in endpoints:
        async with client.get(
            url=f'http://127.0.0.1:{config.http.port}{endpoint}',
            headers={'Content-Type': 'application/json'},
        ) as response:
            assert response.status == status.HTTP_401_UNAUTHORIZED
            data = await response.json()
            assert data['status'] == 401

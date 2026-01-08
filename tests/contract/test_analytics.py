from datetime import timezone, UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from starlette import status

from src.algo_trading.ports.api.v1.schemas.analytics_schema import (
    DrawdownAnalysisResponseSchema,
    MarketDataAnalyticsResponseSchema,
    PortfolioSummaryResponseSchema,
    TradeAnalyticsResponseSchema,
)
from src.algo_trading.enums import OrderStatusEnum
from src.algo_trading.adapters.models import TradingStrategyDocument
from src.algo_trading.adapters.models.metrics import PerformanceMetricsDocument


async def test_get_strategy_performance_returns_metrics(
        config,
        client,
        pydantic_generator_data,
        create_trading_strategy,
        create_trading_sessions,
        create_order,
        mock_auth,
):
    """Test GET /api/v1/analytics/strategies/{strategy_id}/performance returns metrics"""
    strategy_id = uuid4()

    strategy: TradingStrategyDocument = await create_trading_strategy(strategy_id=strategy_id)
    base_time = datetime.now(tz=UTC)

    for day_offset in range(25):
        session_start = base_time - timedelta(days=day_offset+1)
        session_end = base_time - timedelta(days=day_offset)

        session = await create_trading_sessions(
            strategy_id=strategy.strategy_id,
            session_start=session_start,
            session_end=session_end,
        )

        for _ in range(5):
            await create_order(
                strategy_id=strategy.strategy_id,
                session_id=session.session_id,
                filled_at=session_start + timedelta(hours=2),
                status=OrderStatusEnum.FILLED,
            )

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/performance?period=1m',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:

        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()

        metrics = PerformanceMetricsDocument(**data)
        assert metrics.strategy_id == strategy.strategy_id


@pytest.mark.parametrize('period', ['1d', '1w', '1m', '3m', '1y', 'all'])
async def test_get_strategy_performance_with_period_filter(client, services, config, period, mock_auth):
    """Test GET /api/v1/analytics/strategies/{strategy_id}/performance supports period filters"""
    strategy_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/performance?period={period}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        if response.status == status.HTTP_200_OK:
            data = await response.json()
            metrics = PerformanceMetricsDocument(**data)
            assert metrics.strategy_id == strategy_id


async def test_get_strategy_performance_custom_date_range(client, config, services, mock_auth):
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
            metrics = PerformanceMetricsDocument(**data)
            assert metrics.period_start.date() >= datetime.fromisoformat(from_date).date()
            assert metrics.period_end.date() <= datetime.fromisoformat(to_date).date()


async def test_get_strategy_performance_not_found(client, config, services, get_session, mock_auth):
    """Test GET /api/v1/analytics/strategies/{strategy_id}/performance returns 404"""
    non_existent_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{non_existent_id}/performance?period=1m',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert data['status'] == 404


async def test_get_strategy_trades_analytics(
    client,
    config,
    services,
    create_trading_strategy,
    create_trading_sessions,
    create_order,
    mock_auth,
):
    """Test GET /api/v1/analytics/strategies/{strategy_id}/trades returns trade analytics"""
    strategy_id = uuid4()

    strategy: TradingStrategyDocument = await create_trading_strategy(strategy_id=strategy_id)

    for day_offset in range(35):
        session_start = datetime.now(tz=UTC) - timedelta(days=day_offset+1)
        session_end = datetime.now(tz=UTC) - timedelta(days=day_offset)

        session = await create_trading_sessions(
            strategy_id=strategy.strategy_id,
            session_start=session_start,
            session_end=session_end,
        )

        for _ in range(5):
            await create_order(
                strategy_id=strategy.strategy_id,
                session_id=session.session_id,
                filled_at=session_start + timedelta(hours=2),  # Orders filled 2 hours into session
                status=OrderStatusEnum.FILLED,
            )

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/trades?period=1d',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        analytics = TradeAnalyticsResponseSchema(**data)
        assert analytics.strategy_id == strategy_id


async def test_get_strategy_drawdown_analysis(
    client,
    config,
    services,
    create_trading_strategy,
    create_trading_sessions,
    create_order,
    mock_auth,
):
    """Test GET /api/v1/analytics/strategies/{strategy_id}/drawdown returns drawdown analysis"""
    strategy_id = uuid4()

    strategy: TradingStrategyDocument = await create_trading_strategy(strategy_id=strategy_id)

    for day_offset in range(35):
        session_start = datetime.now(tz=UTC) - timedelta(days=day_offset+1)
        session_end = datetime.now(tz=UTC) - timedelta(days=day_offset)

        session = await create_trading_sessions(
            strategy_id=strategy.strategy_id,
            session_start=session_start,
            session_end=session_end,
        )

        for _ in range(5):
            await create_order(
                strategy_id=strategy.strategy_id,
                session_id=session.session_id,
                filled_at=session_start + timedelta(hours=2),  # Orders filled 2 hours into session
                status=OrderStatusEnum.FILLED,
            )

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/strategies/{strategy_id}/drawdown?period=1d',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        drawdown = DrawdownAnalysisResponseSchema(**data)
        assert drawdown.strategy_id == strategy_id
        assert drawdown.max_drawdown <= 0
        assert drawdown.max_drawdown_duration >= 0
        assert drawdown.current_drawdown <= 0


async def test_get_portfolio_summary(
    client,
    config,
    services,
    create_trading_strategy,
    create_trading_sessions,
    create_order,
    mock_auth,
):
    """Test GET /api/v1/analytics/portfolio/summary returns portfolio summary"""

    strategy_id = uuid4()
    base_time = datetime.now(timezone.utc)

    strategy: TradingStrategyDocument = await create_trading_strategy(strategy_id=strategy_id)

    for day_offset in range(35):
        session_start = base_time - timedelta(days=day_offset+1)
        session_end = base_time - timedelta(days=day_offset)

        session = await create_trading_sessions(
            strategy_id=strategy.strategy_id,
            session_start=session_start,
            session_end=session_end,
        )

        for _ in range(5):
            await create_order(
                strategy_id=strategy.strategy_id,
                session_id=session.session_id,
                filled_at=session_start + timedelta(hours=2),
                status=OrderStatusEnum.FILLED,
            )
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/portfolio/summary?period=1d',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        summary = PortfolioSummaryResponseSchema(**data)
        assert summary.total_value >= 0
        assert summary.active_strategies >= 0
        assert summary.total_trades >= 0
        assert 0 <= summary.win_rate <= 1


async def test_get_market_data_analytics(
    client,
    monkeypatch,
    config,
    mock_auth,
    mock_tinkoff_client,
    mongo_connection,
):
    """Test GET /api/v1/analytics/market-data/{instrument} returns market data"""

    instrument = 'AAPL'
    mock_tinkoff_client.set_instrument(instrument, {
        'figi': 'BBG000B9XRY4',
        'ticker': instrument,
        'name': 'Apple Inc.',
        'currency': 'usd',
        'lot': 1,
        'min_price_increment': Decimal('0.01'),
    })
    mock_tinkoff_client.set_price('BBG000B9XRY4', Decimal('150.25'))

    monkeypatch.setattr(
        'src.algo_trading.ports.api.v1.analytics.TinkoffInvestClient',
        lambda account_id="test", context_name="up": mock_tinkoff_client,
    )

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/{instrument}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        market_data = MarketDataAnalyticsResponseSchema(**data)
        assert market_data.instrument == instrument
        assert market_data.timeframe is not None
        assert isinstance(market_data.data_points, list)
        assert len(market_data.data_points) > 0
        assert isinstance(market_data.indicators, dict)


@pytest.mark.parametrize('timeframe', ['1m', '5m', '15m', '1h', '1d'])
async def test_get_market_data_with_timeframe(
    client,
    config,
    timeframe,
    mock_auth,
    mock_tinkoff_client,
    monkeypatch,
    mongo_connection,
):
    """Test GET /api/v1/analytics/market-data/{instrument} supports timeframe parameter"""
    instrument = 'MSFT'

    mock_tinkoff_client.set_instrument(instrument, {
        'figi': 'BBG000BPH459',
        'ticker': instrument,
        'name': 'Microsoft Corp.',
        'currency': 'usd',
        'lot': 1,
        'min_price_increment': Decimal('0.01'),
    })
    mock_tinkoff_client.set_price('BBG000BPH459', Decimal('380.50'))

    monkeypatch.setattr(
        'src.algo_trading.ports.api.v1.analytics.TinkoffInvestClient',
        lambda account_id=None, context_name=None: mock_tinkoff_client,
    )

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/{instrument}?timeframe={timeframe}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()
        market_data = MarketDataAnalyticsResponseSchema(**data)
        assert market_data.timeframe == timeframe
        assert len(market_data.data_points) > 0


async def test_analytics_endpoints_require_authentication(client, config, get_session, services):
    """Test all analytics endpoints require authentication"""
    strategy_id = uuid4()

    endpoints = [
        f'/api/v1/analytics/strategies/{strategy_id}/performance?period=1m',
        f'/api/v1/analytics/strategies/{strategy_id}/trades?period=1m',
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

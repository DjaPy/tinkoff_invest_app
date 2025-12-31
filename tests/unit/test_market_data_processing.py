"""Unit tests for market data processing logic (T083).

Tests cover:
1. Error handling and exception wrapping
2. Price fetching (current price by ticker and FIGI)
3. Analytics data formatting

These tests use mocks for external dependencies (TinkoffClient, MongoDB).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.algo_trading.adapters.models.market_data import MarketDataDocument
from src.algo_trading.services.market_data import MarketDataError, MarketDataService


async def test_get_current_price_handles_client_error():
    """Test that client errors are wrapped in MarketDataError."""
    mock_client = AsyncMock()
    mock_client.get_market_price.side_effect = Exception('API connection failed')

    service = MarketDataService(mock_client)

    with pytest.raises(MarketDataError) as exc_info:
        await service.get_current_price('AAPL')

    assert 'Failed to get current price for AAPL' in str(exc_info.value)
    assert 'API connection failed' in str(exc_info.value)


async def test_get_current_price_by_figi_handles_client_error():
    """Test that FIGI price fetch errors are wrapped in MarketDataError."""
    mock_client = AsyncMock()
    mock_client.get_last_price.side_effect = Exception('FIGI not found')

    service = MarketDataService(mock_client)

    with pytest.raises(MarketDataError) as exc_info:
        await service.get_current_price_by_figi('BBG000B9XRY4')

    assert 'Failed to get current price for FIGI BBG000B9XRY4' in str(exc_info.value)
    assert 'FIGI not found' in str(exc_info.value)


async def test_get_current_price_success():
    """Test successful current price fetch."""
    mock_client = AsyncMock()
    mock_client.get_market_price.return_value = Decimal('150.25')

    service = MarketDataService(mock_client)

    price = await service.get_current_price('AAPL')

    assert price == Decimal('150.25')
    mock_client.get_market_price.assert_called_once_with('AAPL')


async def test_get_current_price_by_figi_success():
    """Test successful FIGI price fetch."""
    mock_client = AsyncMock()
    mock_client.get_last_price.return_value = Decimal('380.50')

    service = MarketDataService(mock_client)

    price = await service.get_current_price_by_figi('BBG000BPH459')

    assert price == Decimal('380.50')
    mock_client.get_last_price.assert_called_once_with('BBG000BPH459')



async def test_get_market_data_analytics_formats_data_correctly(mongo_connection):
    """Test that analytics data is formatted correctly."""
    mock_data = []
    base_time = datetime.now(timezone.utc)

    for i in range(3):
        mock_doc = MagicMock()
        mock_doc.timestamp = base_time - timedelta(days=i)
        mock_doc.open_price = Decimal('100.00') + Decimal(i)
        mock_doc.high_price = Decimal('105.00') + Decimal(i)
        mock_doc.low_price = Decimal('98.00') + Decimal(i)
        mock_doc.close_price = Decimal('103.00') + Decimal(i)
        mock_doc.volume = 1000000 + (i * 100000)
        mock_data.append(mock_doc)

    mock_client = AsyncMock()
    service = MarketDataService(mock_client)

    with patch.object(service, 'get_or_fetch_data', return_value=mock_data):
        analytics = await service.get_market_data_analytics('AAPL', '1d', 100, 60)

    assert analytics['instrument'] == 'AAPL'
    assert analytics['timeframe'] == '1d'
    assert len(analytics['data_points']) == 3
    assert isinstance(analytics['indicators'], dict)
    assert analytics['last_updated'] == mock_data[0].timestamp

    first_point = analytics['data_points'][0]
    assert 'timestamp' in first_point
    assert first_point['open'] == float(Decimal('100.00'))
    assert first_point['high'] == float(Decimal('105.00'))
    assert first_point['low'] == float(Decimal('98.00'))
    assert first_point['close'] == float(Decimal('103.00'))
    assert first_point['volume'] == 1000000


async def test_get_market_data_analytics_empty_data_uses_current_time(mongo_connection):
    """Test that analytics with no data uses current time for last_updated."""
    mock_client = AsyncMock()
    service = MarketDataService(mock_client)

    with patch.object(service, 'get_or_fetch_data', return_value=[]):
        before = datetime.now(timezone.utc)
        analytics = await service.get_market_data_analytics('AAPL', '1d', 100, 60)
        after = datetime.now(timezone.utc)

    assert analytics['instrument'] == 'AAPL'
    assert analytics['timeframe'] == '1d'
    assert len(analytics['data_points']) == 0
    assert isinstance(analytics['indicators'], dict)

    last_updated = analytics['last_updated']
    assert before <= last_updated <= after


async def test_get_market_data_analytics_preserves_parameters(mongo_connection):
    """Test that analytics preserves input parameters."""
    mock_client = AsyncMock()
    service = MarketDataService(mock_client)

    with patch.object(service, 'get_or_fetch_data', return_value=[]):
        analytics = await service.get_market_data_analytics('MSFT', '5m', 50, 30)

    assert analytics['instrument'] == 'MSFT'
    assert analytics['timeframe'] == '5m'


async def test_refresh_data_handles_errors():
    """Test that refresh_data wraps errors correctly."""
    mock_client = AsyncMock()
    service = MarketDataService(mock_client)

    with patch.object(service, 'get_historical_data', side_effect=Exception('Network error')):
        with pytest.raises(MarketDataError) as exc_info:
            await service.refresh_data('AAPL', '1d')

        assert 'Failed to refresh data for AAPL' in str(exc_info.value)
        assert 'Network error' in str(exc_info.value)


async def test_refresh_data_calls_get_historical_data():
    """Test that refresh_data delegates to get_historical_data."""
    mock_client = AsyncMock()
    service = MarketDataService(mock_client)

    with patch.object(service, 'get_historical_data', return_value=[]) as mock_get_hist:
        await service.refresh_data('AAPL', '1h')

        mock_get_hist.assert_called_once_with('AAPL', '1h', limit=100)


async def test_cleanup_old_data_deletes_stale_records(mongo_connection):
    """Test that cleanup_old_data removes records older than specified days."""

    old_timestamp = datetime.now(timezone.utc) - timedelta(days=100)
    recent_timestamp = datetime.now(timezone.utc) - timedelta(days=30)

    old_doc = MarketDataDocument(
        instrument='AAPL',
        timeframe='1d',
        timestamp=old_timestamp,
        open_price=Decimal('100.00'),
        high_price=Decimal('105.00'),
        low_price=Decimal('98.00'),
        close_price=Decimal('103.00'),
        volume=1000000,
    )
    await old_doc.insert()

    recent_doc = MarketDataDocument(
        instrument='AAPL',
        timeframe='1d',
        timestamp=recent_timestamp,
        open_price=Decimal('110.00'),
        high_price=Decimal('115.00'),
        low_price=Decimal('108.00'),
        close_price=Decimal('113.00'),
        volume=1200000,
    )
    await recent_doc.insert()

    mock_client = AsyncMock()
    service = MarketDataService(mock_client)

    deleted_count = await service.cleanup_old_data(days_to_keep=90)

    assert deleted_count == 1
    remaining = await MarketDataDocument.find().to_list()
    assert len(remaining) == 1
    assert remaining[0].timestamp.replace(microsecond=0) == recent_timestamp.replace(tzinfo=None, microsecond=0)


async def test_cleanup_old_data_handles_no_old_data(mongo_connection):
    """Test that cleanup_old_data handles case with no old data."""
    mock_client = AsyncMock()
    service = MarketDataService(mock_client)

    deleted_count = await service.cleanup_old_data(days_to_keep=90)

    assert deleted_count == 0

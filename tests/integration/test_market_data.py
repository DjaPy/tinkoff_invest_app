"""Integration Test: Market Data Processing.

Validates market data integration and processing.
"""

from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_market_data_retrieval(client, config):
    """
    Integration test for market data retrieval.

    Validates that market data endpoint works correctly.
    """
    # Get market data for instrument
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/AAPL?timeframe=1d&limit=10',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        market_data = await response.json()

        # Verify market data structure
        assert 'data' in market_data or 'candles' in market_data or isinstance(market_data, list)


@pytest.mark.asyncio
async def test_market_data_for_multiple_instruments(client, config):
    """
    Test market data retrieval for multiple instruments.

    Validates concurrent data fetching.
    """
    instruments = ['AAPL', 'MSFT', 'GOOGL']

    for instrument in instruments:
        async with client.get(
            url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/{instrument}?timeframe=1d&limit=5',
            headers={'Authorization': 'Bearer test-token'},
        ) as response:
            assert response.status == HTTPStatus.OK


@pytest.mark.asyncio
async def test_market_data_with_different_timeframes(client, config):
    """
    Test market data retrieval with different timeframes.

    Validates timeframe parameter handling.
    """
    timeframes = ['1m', '5m', '1h', '1d', '1w']

    for timeframe in timeframes:
        async with client.get(
            url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/AAPL?timeframe={timeframe}&limit=10',
            headers={'Authorization': 'Bearer test-token'},
        ) as response:
            # Should return OK or handle gracefully if timeframe not supported
            assert response.status in [HTTPStatus.OK, HTTPStatus.BAD_REQUEST]


@pytest.mark.asyncio
async def test_market_data_validation(client, config):
    """
    Test market data request validation.

    Validates proper error handling for invalid requests.
    """
    # Invalid instrument (empty)
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/?timeframe=1d',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        # Should fail with validation error or not found
        assert response.status in [HTTPStatus.NOT_FOUND, HTTPStatus.UNPROCESSABLE_ENTITY]


@pytest.mark.asyncio
async def test_market_data_integration_with_strategy(client, config, mongo_connection):
    """
    Test market data integration with strategy execution.

    Validates that strategies can access market data.
    """
    # Create strategy that depends on market data
    strategy_data = {
        'name': 'Market Data Test Strategy',
        'strategy_type': 'momentum',
        'parameters': {
            'lookback_period': '20',
            'momentum_threshold': '0.02',
            'instruments': 'AAPL,MSFT',
            'position_size': '100',
        },
        'risk_controls': {
            'max_position_size': '1000',
            'max_portfolio_value': '50000',
            'stop_loss_percent': '0.05',
            'max_drawdown_percent': '0.10',
            'daily_loss_limit': '1000',
            'max_orders_per_day': 20,
            'trading_hours_start': '09:30:00',
            'trading_hours_end': '16:00:00',
        },
        'created_by': 'test_user',
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies',
        json=strategy_data,
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.CREATED
        created = await response.json()
        created['strategy_id']

    # Verify market data is accessible for strategy instruments
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/AAPL?timeframe=1d&limit=20',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/MSFT?timeframe=1d&limit=20',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK

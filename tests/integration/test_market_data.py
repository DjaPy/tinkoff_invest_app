"""Integration Test: Market Data Processing.

Validates market data integration and processing.
"""

from decimal import Decimal
from http import HTTPStatus


async def test_market_data_retrieval(client, config, mock_auth, mock_tinkoff_client, monkeypatch, mongo_connection):
    """
    Integration test for market data retrieval.

    Validates that market data endpoint works correctly.
    """
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
        lambda account_id=None, context_name=None: mock_tinkoff_client,
    )

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/AAPL?timeframe=1d&limit=10',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.OK
        market_data = await response.json()

        # Market data should contain expected fields
        assert 'instrument' in market_data
        assert 'data_points' in market_data or 'candles' in market_data or isinstance(market_data, list)



async def test_market_data_for_multiple_instruments(
    client,
    config,
    mock_auth,
    mock_tinkoff_client,
    monkeypatch,
    mongo_connection,
):
    """
    Test market data retrieval for multiple instruments.

    Validates concurrent data fetching.
    """
    instruments_data = {
        'AAPL': {'figi': 'BBG000B9XRY4', 'price': Decimal('150.25')},
        'MSFT': {'figi': 'BBG000BPH459', 'price': Decimal('380.50')},
        'GOOGL': {'figi': 'BBG009S39JX6', 'price': Decimal('2800.75')},
    }

    for ticker, data in instruments_data.items():
        mock_tinkoff_client.set_instrument(ticker, {
            'figi': data['figi'],
            'ticker': ticker,
            'name': f'{ticker} Company',
            'currency': 'usd',
            'lot': 1,
            'min_price_increment': Decimal('0.01'),
        })
        mock_tinkoff_client.set_price(data['figi'], data['price'])

    monkeypatch.setattr(
        'src.algo_trading.ports.api.v1.analytics.TinkoffInvestClient',
        lambda account_id=None, context_name=None: mock_tinkoff_client,
    )

    for instrument in instruments_data:
        async with client.get(
            url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/{instrument}?timeframe=1d&limit=5',
            headers={'Authorization': 'Bearer test-token'},
        ) as response:
            assert response.status == HTTPStatus.OK



async def test_market_data_with_different_timeframes(
    client,
    config,
    mock_auth,
    mock_tinkoff_client,
    monkeypatch,
    mongo_connection,
):
    """
    Test market data retrieval with different timeframes.

    Validates timeframe parameter handling.
    """
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
        lambda account_id=None, context_name=None: mock_tinkoff_client,
    )

    timeframes = ['1m', '5m', '1h', '1d', '1w']

    for timeframe in timeframes:
        async with client.get(
            url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/AAPL/?timeframe={timeframe}&limit=10',
            headers={'Authorization': 'Bearer test-token'},
        ) as response:
            assert response.status == HTTPStatus.OK


async def test_market_data_validation(
    client,
    config,
    mock_auth,
):
    """
    Test market data request validation.

    Validates proper error handling for invalid query parameters.
    """
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/AAPL?timeframe=1d&limit=2000',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/analytics/market-data/AAPL?timeframe=1d&limit=-1',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY


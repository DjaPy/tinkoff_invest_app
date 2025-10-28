"""Market Data Service - Application Layer.

Provides real-time and historical market data using Tinkoff Invest API.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from tinkoff.invest import CandleInterval

from src.algo_trading.adapters.models.market_data import MarketData
from src.algo_trading.adapters.tinkoff_client import TinkoffInvestClient


class MarketDataError(Exception):
    """Market data operation failed."""


class MarketDataService:
    """
    Service for market data operations.

    Handles fetching and caching of real-time and historical market data.
    """

    def __init__(self, tinkoff_client: TinkoffInvestClient) -> None:
        """
        Initialize market data service.

        Args:
            tinkoff_client: Tinkoff Invest API client
        """
        self.client = tinkoff_client

    async def get_current_price(self, ticker: str) -> Decimal:
        """
        Get current market price for instrument.

        Args:
            ticker: Instrument ticker

        Returns:
            Current price

        Raises:
            MarketDataError: If price fetch fails
        """
        try:
            return await self.client.get_market_price(ticker)
        except Exception as e:
            raise MarketDataError(f'Failed to get current price for {ticker}: {e}') from e

    async def get_current_price_by_figi(self, figi: str) -> Decimal:
        """
        Get current market price by FIGI.

        Args:
            figi: Financial Instrument Global Identifier

        Returns:
            Current price

        Raises:
            MarketDataError: If price fetch fails
        """
        try:
            return await self.client.get_last_price(figi)
        except Exception as e:
            raise MarketDataError(f'Failed to get current price for FIGI {figi}: {e}') from e

    async def get_historical_data(self, ticker: str, timeframe: str = '1d', limit: int = 100) -> list[MarketData]:
        """
        Get historical market data.

        Args:
            ticker: Instrument ticker
            timeframe: Timeframe (1m, 5m, 1h, 1d, 1w)
            limit: Number of candles to fetch

        Returns:
            List of market data candles

        Raises:
            MarketDataError: If data fetch fails
        """
        try:
            # Get instrument FIGI
            instrument = await self.client.get_instrument_by_ticker(ticker)
            figi = instrument['figi']

            # Map timeframe to CandleInterval
            interval_map = {
                '1m': CandleInterval.CANDLE_INTERVAL_1_MIN,
                '5m': CandleInterval.CANDLE_INTERVAL_5_MIN,
                '15m': CandleInterval.CANDLE_INTERVAL_15_MIN,
                '1h': CandleInterval.CANDLE_INTERVAL_HOUR,
                '1d': CandleInterval.CANDLE_INTERVAL_DAY,
                '1w': CandleInterval.CANDLE_INTERVAL_WEEK,
            }

            interval = interval_map.get(timeframe, CandleInterval.CANDLE_INTERVAL_DAY)

            # Calculate time range based on limit and timeframe
            to_time = datetime.utcnow()
            if timeframe == '1m':
                from_time = to_time - timedelta(minutes=limit)
            elif timeframe == '5m':
                from_time = to_time - timedelta(minutes=5 * limit)
            elif timeframe == '15m':
                from_time = to_time - timedelta(minutes=15 * limit)
            elif timeframe == '1h':
                from_time = to_time - timedelta(hours=limit)
            elif timeframe == '1w':
                from_time = to_time - timedelta(weeks=limit)
            else:  # 1d
                from_time = to_time - timedelta(days=limit)

            # Fetch candles from Tinkoff
            candles = await self.client.get_candles(figi=figi, interval=interval, from_time=from_time, to_time=to_time)

            # Convert to MarketData models and save to database
            market_data_list = []
            for candle in candles:
                market_data = MarketData(
                    instrument=ticker,
                    timeframe=timeframe,
                    timestamp=candle['time'],
                    open_price=candle['open'],
                    high_price=candle['high'],
                    low_price=candle['low'],
                    close_price=candle['close'],
                    volume=candle['volume'],
                )
                await market_data.insert()
                market_data_list.append(market_data)

            return market_data_list
        except Exception as e:
            raise MarketDataError(f'Failed to get historical data for {ticker}: {e}') from e

    async def get_cached_data(self, ticker: str, timeframe: str = '1d', limit: int = 100) -> list[MarketData]:
        """
        Get cached market data from database.

        Args:
            ticker: Instrument ticker
            timeframe: Timeframe
            limit: Max number of records

        Returns:
            List of cached market data

        Raises:
            MarketDataError: If data fetch fails
        """
        try:
            # Query from database
            return (
                await MarketData.find(MarketData.instrument == ticker, MarketData.timeframe == timeframe)
                .sort('-timestamp')
                .limit(limit)
                .to_list()
            )

        except Exception as e:
            raise MarketDataError(f'Failed to get cached data for {ticker}: {e}') from e

    async def get_or_fetch_data(
        self,
        ticker: str,
        timeframe: str = '1d',
        limit: int = 100,
        max_age_minutes: int = 60,
    ) -> list[MarketData]:
        """
        Get market data from cache or fetch if stale.

        Args:
            ticker: Instrument ticker
            timeframe: Timeframe
            limit: Number of candles
            max_age_minutes: Max cache age in minutes

        Returns:
            List of market data

        Raises:
            MarketDataError: If data fetch fails
        """
        # Try to get cached data
        cached_data = await self.get_cached_data(ticker, timeframe, limit)

        # Check if cache is fresh enough
        if cached_data:
            latest = cached_data[0]
            age = datetime.utcnow() - latest.timestamp
            if age.total_seconds() < max_age_minutes * 60:
                return cached_data

        # Cache is stale or empty, fetch new data
        return await self.get_historical_data(ticker, timeframe, limit)

    async def refresh_data(self, ticker: str, timeframe: str = '1d') -> None:
        """
        Refresh market data for instrument.

        Args:
            ticker: Instrument ticker
            timeframe: Timeframe to refresh

        Raises:
            MarketDataError: If refresh fails
        """
        try:
            await self.get_historical_data(ticker, timeframe, limit=100)
        except Exception as e:
            raise MarketDataError(f'Failed to refresh data for {ticker}: {e}') from e

"""Market Data Service - Application Layer.

Provides real-time and historical market data using Tinkoff Invest API.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from t_tech.invest import CandleInterval

from src.algo_trading.adapters.models.market_data import MarketDataDocument
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

    async def get_historical_data(
        self,
        ticker: str,
        timeframe: str = '1d',
        limit: int = 100,
    ) -> list[MarketDataDocument]:
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
            instrument = await self.client.get_instrument_by_ticker(ticker)
            figi = instrument['figi']

            interval_map = {
                '1m': CandleInterval.CANDLE_INTERVAL_1_MIN,
                '5m': CandleInterval.CANDLE_INTERVAL_5_MIN,
                '15m': CandleInterval.CANDLE_INTERVAL_15_MIN,
                '1h': CandleInterval.CANDLE_INTERVAL_HOUR,
                '1d': CandleInterval.CANDLE_INTERVAL_DAY,
                '1w': CandleInterval.CANDLE_INTERVAL_WEEK,
            }

            interval = interval_map.get(timeframe, CandleInterval.CANDLE_INTERVAL_DAY)

            to_time = datetime.now(timezone.utc)
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
            else:
                from_time = to_time - timedelta(days=limit)

            candles = await self.client.get_candles(figi=figi, interval=interval, from_time=from_time, to_time=to_time)

            if not candles:
                return []

            market_data_list = [
                MarketDataDocument(
                    instrument=ticker,
                    timeframe=timeframe,
                    timestamp=candle['time'],
                    open_price=candle['open'],
                    high_price=candle['high'],
                    low_price=candle['low'],
                    close_price=candle['close'],
                    volume=candle['volume'],
                )
                for candle in candles
            ]

            await MarketDataDocument.insert_many(market_data_list)

            return market_data_list
        except Exception as e:
            raise MarketDataError(f'Failed to get historical data for {ticker}: {e}') from e

    async def get_cached_data(self, ticker: str, timeframe: str = '1d', limit: int = 100) -> list[MarketDataDocument]:
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
            return (
                await MarketDataDocument.find(
                    MarketDataDocument.instrument == ticker,
                    MarketDataDocument.timeframe == timeframe,
                )
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
    ) -> list[MarketDataDocument]:
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
        cached_data = await self.get_cached_data(ticker, timeframe, limit)

        if cached_data:
            latest = cached_data[0]
            age = datetime.now(timezone.utc) - latest.timestamp
            if age.total_seconds() < max_age_minutes * 60:
                return cached_data

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

    async def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """
        Delete market data older than specified days.

        Args:
            days_to_keep: Number of days to keep (default: 90)

        Returns:
            Number of deleted documents

        Raises:
            MarketDataError: If cleanup fails
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

            result = await MarketDataDocument.find(MarketDataDocument.timestamp < cutoff_date).delete()

            return result.deleted_count if result else 0

        except Exception as e:
            raise MarketDataError(f'Failed to cleanup old data: {e}') from e

    async def get_market_data_analytics(
        self,
        ticker: str,
        timeframe: str = '1d',
        limit: int = 100,
        max_age_minutes: int = 60,
    ) -> dict[str, Any]:
        """
        Get market data analytics with formatted data points.

        Args:
            ticker: Instrument ticker
            timeframe: Timeframe
            limit: Number of candles
            max_age_minutes: Max cache age in minutes

        Returns:
            Dictionary with instrument, timeframe, data_points, indicators, last_updated

        Raises:
            MarketDataError: If data fetch fails
        """
        market_data_list = await self.get_or_fetch_data(ticker, timeframe, limit, max_age_minutes)

        data_points = [
            {
                'timestamp': md.timestamp.isoformat(),
                'open': float(md.open_price),
                'high': float(md.high_price),
                'low': float(md.low_price),
                'close': float(md.close_price),
                'volume': md.volume,
            }
            for md in market_data_list
        ]

        last_updated = market_data_list[0].timestamp if market_data_list else datetime.now(timezone.utc)

        return {
            'instrument': ticker,
            'timeframe': timeframe,
            'data_points': data_points,
            'indicators': {},
            'last_updated': last_updated,
        }

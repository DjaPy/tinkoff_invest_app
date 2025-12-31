"""MarketData Beanie model - Hexagonal Architecture Adapter."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from src.algo_trading.adapters.models.common import DecimalField


class MarketDataDocument(Document):
    """
    Real-time and historical market data (candles/OHLCV).

    Stores OHLCV data (open, high, low, close, volume) for different timeframes.
    Follows Hexagonal Architecture as an Adapter (infrastructure layer).
    """

    data_id: UUID = Field(default_factory=uuid4, description='Unique data point identifier')
    instrument: str = Field(min_length=1, description='Trading instrument')
    timeframe: str = Field(description='Candle timeframe (1m, 5m, 1h, 1d, etc.)')
    timestamp: datetime = Field(description='Candle timestamp')

    open_price: DecimalField = Field(gt=0, description='Opening price')
    high_price: DecimalField = Field(gt=0, description='High price')
    low_price: DecimalField = Field(gt=0, description='Low price')
    close_price: DecimalField = Field(gt=0, description='Closing price')
    volume: int = Field(ge=0, description='Trading volume')

    indicators: dict[str, Any] = Field(default_factory=dict, description='Technical indicators (RSI, MACD, etc.)')

    data_source: str = Field(default='tinkoff', description='Data provider identifier')

    @field_validator('high_price', mode='after')
    @classmethod
    def validate_high_price(cls, v: Decimal, values: ValidationInfo) -> Decimal:
        """High price must be >= low price."""
        low_price = values.data.get('low_price')
        if low_price is not None and v < low_price:
            raise ValueError(f'High price {v} cannot be less than low price {low_price}')
        return v

    @field_validator('low_price', mode='after')
    @classmethod
    def validate_low_price(cls, v: Decimal, values: ValidationInfo) -> Decimal:
        """Low price must be <= open and close prices."""
        open_price = values.data.get('open_price')
        if open_price is not None and v > open_price:
            raise ValueError(f'Low price {v} cannot be greater than open price {open_price}')
        return v

    def is_stale(self, max_age_seconds: int = 60) -> bool:
        """Check if market data is stale."""

        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age > max_age_seconds

    class Settings:
        name = 'market_data'
        indexes = [
            'data_id',
            [('instrument', 1), ('timestamp', -1)],  # Latest data first
            'timestamp',
            'data_source',
        ]

"""MarketData Beanie model - Hexagonal Architecture Adapter."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo


class MarketData(Document):
    """
    Real-time and historical market data.

    Stores price, volume, bid/ask, and technical indicators.
    Follows Hexagonal Architecture as an Adapter (infrastructure layer).
    """

    data_id: UUID = Field(default_factory=uuid4, description="Unique data point identifier")
    instrument: str = Field(min_length=1, description="Trading instrument")
    timestamp: datetime = Field(description="Market data timestamp")

    price: Decimal = Field(gt=0, description="Current/historical price")
    volume: int = Field(ge=0, description="Trading volume")

    bid: Decimal | None = Field(None, gt=0, description="Best bid price")
    ask: Decimal | None = Field(None, gt=0, description="Best ask price")
    spread: Decimal | None = Field(None, ge=0, description="Bid-ask spread")

    indicators: dict[str, Any] = Field(default_factory=dict, description="Technical indicators (RSI, MACD, etc.)")

    data_source: str = Field(description="Data provider identifier")

    @field_validator("ask", mode='after')
    @classmethod
    def validate_bid_ask(cls, v: Decimal | None, values: ValidationInfo) -> Decimal | None:
        """Ask must be greater than or equal to bid."""
        bid = values.data.get("bid")
        if bid is not None and v is not None and v < bid:
            raise ValueError(f"Ask price {v} cannot be less than bid price {bid}")
        return v

    @field_validator("spread", mode='after')
    @classmethod
    def validate_spread(cls, v: Decimal | None, values: ValidationInfo) -> Decimal | None:
        """Calculate spread if bid and ask are provided."""
        bid = values.data.get("bid")
        ask = values.data.get("ask")

        if bid is not None and ask is not None:
            calculated_spread = ask - bid
            if v is None:
                return calculated_spread
            elif abs(v - calculated_spread) > Decimal("0.01"):
                raise ValueError(
                    f"Spread {v} doesn't match calculated spread {calculated_spread}"
                )

        return v

    def calculate_mid_price(self) -> Decimal | None:
        """Calculate mid-price from bid/ask."""
        if self.bid is None or self.ask is None:
            return None

        return (self.bid + self.ask) / Decimal("2")

    def is_stale(self, max_age_seconds: int = 60) -> bool:
        """Check if market data is stale."""
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > max_age_seconds

    class Settings:
        name = "market_data"
        indexes = [
            "data_id",
            [("instrument", 1), ("timestamp", -1)],  # Latest data first
            "timestamp",
            "data_source",
        ]

"""PortfolioPosition Beanie model - Hexagonal Architecture Adapter."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field, computed_field


class PortfolioPosition(Document):
    """
    Current holdings and P&L for a trading instrument.

    Tracks position size, cost basis, and unrealized profit/loss.
    Follows Hexagonal Architecture as an Adapter (infrastructure layer).
    """

    position_id: UUID = Field(default_factory=uuid4, description='Unique position identifier')
    strategy_id: UUID = Field(description='Strategy holding this position')
    instrument: str = Field(min_length=1, description='Trading instrument')

    quantity: Decimal = Field(description='Position size (positive=long, negative=short)')
    average_price: Decimal = Field(gt=0, description='Average cost basis')
    current_price: Decimal = Field(gt=0, description='Current market price')

    updated_at: datetime = Field(default_factory=datetime.utcnow, description='Last update timestamp')

    @computed_field  # type: ignore[prop-decorator]
    @property
    def unrealized_pnl(self) -> Decimal:
        """Calculate unrealized profit/loss."""
        if self.quantity == 0:
            return Decimal('0')

        price_diff = self.current_price - self.average_price
        return price_diff * self.quantity

    @computed_field  # type: ignore[prop-decorator]
    @property
    def market_value(self) -> Decimal:
        """Calculate current market value."""
        return abs(self.quantity) * self.current_price

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pnl_percent(self) -> Decimal:
        """Calculate P&L as percentage of cost basis."""
        if self.average_price == 0:
            return Decimal('0')

        return (self.current_price - self.average_price) / self.average_price * Decimal('100')

    def update_price(self, new_price: Decimal) -> None:
        """Update current market price."""
        if new_price <= 0:
            raise ValueError('Price must be positive')

        self.current_price = new_price
        self.updated_at = datetime.utcnow()

    def add_trade(self, quantity: Decimal, price: Decimal) -> None:
        """
        Update position after trade execution.

        Uses weighted average for cost basis calculation.
        """
        if price <= 0:
            raise ValueError('Trade price must be positive')

        # Calculate new average price
        if (self.quantity > 0 and quantity > 0) or (self.quantity < 0 and quantity < 0):
            # Same direction - update average
            total_cost = (abs(self.quantity) * self.average_price) + (abs(quantity) * price)
            new_quantity = self.quantity + quantity
            if new_quantity != 0:
                self.average_price = total_cost / abs(new_quantity)
            self.quantity = new_quantity
        else:
            # Opposite direction - reduce or flip position
            self.quantity += quantity
            if self.quantity * quantity > 0:  # Position flipped
                self.average_price = price

        self.updated_at = datetime.utcnow()

    class Settings:
        name = 'portfolio_positions'
        indexes = [
            'position_id',
            [('strategy_id', 1), ('instrument', 1)],  # Unique per strategy+instrument
            'updated_at',
        ]

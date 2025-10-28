"""
Position Repository - Hexagonal Architecture Adapter.

Provides data access operations for portfolio positions with real-time updates.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.algo_trading.adapters.models.position import PortfolioPosition


class PositionRepository:
    """
    Repository for portfolio position persistence with real-time updates.

    Implements outbound port for position data access.
    Supports real-time position tracking and P&L calculations.
    """

    async def create_or_update_position(
        self,
        strategy_id: UUID,
        instrument: str,
        quantity: int,
        average_price: Decimal,
        current_price: Decimal,
    ) -> PortfolioPosition:
        """
        Create new position or update existing one.

        Args:
            strategy_id: Strategy UUID
            instrument: Trading instrument
            quantity: Position quantity (positive for long, negative for short)
            average_price: Average entry price
            current_price: Current market price

        Returns:
            Created or updated position

        Note:
            Automatically calculates unrealized P&L based on prices.
        """
        # Try to find existing position
        existing = await self.find_by_strategy_and_instrument(strategy_id, instrument)

        if existing:
            # Update existing position
            existing.quantity = Decimal(str(quantity))
            existing.average_price = average_price
            existing.current_price = current_price
            existing.updated_at = datetime.utcnow()
            await existing.save()
            return existing
        # Create new position
        position = PortfolioPosition(
            strategy_id=strategy_id,
            instrument=instrument,
            quantity=Decimal(str(quantity)),
            average_price=average_price,
            current_price=current_price,
        )
        await position.insert()
        return position

    async def find_by_id(self, position_id: UUID) -> PortfolioPosition | None:
        """
        Find position by ID.

        Args:
            position_id: Position UUID

        Returns:
            Position if found, None otherwise
        """
        return await PortfolioPosition.find_one(PortfolioPosition.position_id == position_id)

    async def find_by_strategy(self, strategy_id: UUID, include_closed: bool = False) -> list[PortfolioPosition]:
        """
        Find all positions for a strategy.

        Args:
            strategy_id: Strategy UUID
            include_closed: Include closed positions (quantity = 0)

        Returns:
            List of positions sorted by instrument
        """
        query = PortfolioPosition.find(PortfolioPosition.strategy_id == strategy_id)

        if not include_closed:
            query = query.find(PortfolioPosition.quantity != 0)

        return await query.sort('instrument').to_list()

    async def find_by_strategy_and_instrument(self, strategy_id: UUID, instrument: str) -> PortfolioPosition | None:
        """
        Find position for specific strategy and instrument.

        Args:
            strategy_id: Strategy UUID
            instrument: Trading instrument

        Returns:
            Position if found, None otherwise
        """
        return await PortfolioPosition.find_one(
            PortfolioPosition.strategy_id == strategy_id,
            PortfolioPosition.instrument == instrument,
        )

    async def update_market_price(self, position_id: UUID, new_price: Decimal) -> PortfolioPosition:
        """
        Update current market price for real-time P&L tracking.

        Args:
            position_id: Position UUID
            new_price: New market price

        Returns:
            Updated position with recalculated unrealized P&L

        Raises:
            ValueError: If position not found
        """
        position = await self.find_by_id(position_id)
        if not position:
            raise ValueError(f'Position {position_id} not found')

        position.current_price = new_price
        position.updated_at = datetime.utcnow()

        await position.save()
        return position

    async def update_market_prices_bulk(self, price_updates: dict[str, Decimal]) -> list[PortfolioPosition]:
        """
        Bulk update market prices for multiple instruments.

        Args:
            price_updates: Dictionary mapping instrument to new price

        Returns:
            List of updated positions

        Note:
            Efficient for real-time market data feeds updating multiple positions.
        """
        updated_positions = []

        for instrument, new_price in price_updates.items():
            # Find all positions for this instrument
            positions = await PortfolioPosition.find(
                PortfolioPosition.instrument == instrument,
                PortfolioPosition.quantity != 0,
            ).to_list()

            for position in positions:
                position.current_price = new_price
                position.updated_at = datetime.utcnow()
                await position.save()
                updated_positions.append(position)

        return updated_positions

    async def adjust_position(self, position_id: UUID, quantity_delta: int, trade_price: Decimal) -> PortfolioPosition:
        """
        Adjust position quantity and recalculate average price.

        Args:
            position_id: Position UUID
            quantity_delta: Change in quantity (positive = buy, negative = sell)
            trade_price: Trade execution price

        Returns:
            Updated position with new average price

        Raises:
            ValueError: If position not found

        Note:
            Uses weighted average for new average price calculation.
        """
        position = await self.find_by_id(position_id)
        if not position:
            raise ValueError(f'Position {position_id} not found')

        old_quantity = position.quantity
        new_quantity = old_quantity + quantity_delta

        # Recalculate average price
        if new_quantity == 0:
            # Position closed
            position.quantity = Decimal('0')
            position.realized_pnl += (trade_price - position.average_price) * Decimal(str(abs(quantity_delta)))
        elif (old_quantity > 0 and quantity_delta > 0) or (old_quantity < 0 and quantity_delta < 0):
            # Adding to existing position - recalculate average
            total_cost = position.average_price * abs(old_quantity) + trade_price * Decimal(str(abs(quantity_delta)))
            position.average_price = total_cost / abs(new_quantity)
            position.quantity = Decimal(str(new_quantity))
        else:
            # Reducing position - realize P&L
            realized_qty = Decimal(str(min(abs(quantity_delta), abs(old_quantity))))
            position.realized_pnl += (
                (trade_price - position.average_price) * realized_qty * Decimal('-1' if old_quantity < 0 else '1')
            )
            position.quantity = Decimal(str(new_quantity))

        position.updated_at = datetime.utcnow()
        await position.save()
        return position

    async def close_position(self, position_id: UUID, exit_price: Decimal) -> PortfolioPosition:
        """
        Close position and realize final P&L.

        Args:
            position_id: Position UUID
            exit_price: Exit price for closing

        Returns:
            Closed position with realized P&L

        Raises:
            ValueError: If position not found or already closed
        """
        position = await self.find_by_id(position_id)
        if not position:
            raise ValueError(f'Position {position_id} not found')

        if position.quantity == 0:
            raise ValueError(f'Position {position_id} is already closed')

        # Calculate final realized P&L
        final_pnl = (exit_price - position.average_price) * position.quantity
        position.realized_pnl += final_pnl
        position.quantity = Decimal('0')
        position.current_price = exit_price
        position.updated_at = datetime.utcnow()

        await position.save()
        return position

    async def get_portfolio_summary(self, strategy_id: UUID) -> dict:
        """
        Get portfolio summary for a strategy.

        Args:
            strategy_id: Strategy UUID

        Returns:
            Dictionary with portfolio metrics:
            - total_positions: Number of open positions
            - total_market_value: Sum of all position market values
            - total_unrealized_pnl: Sum of unrealized P&L
            - total_realized_pnl: Sum of realized P&L
            - total_pnl: Total P&L (realized + unrealized)
            - positions: List of positions with details
        """
        positions = await self.find_by_strategy(strategy_id, include_closed=False)

        total_market_value = Decimal('0')
        total_unrealized_pnl = Decimal('0')
        total_realized_pnl = Decimal('0')

        for position in positions:
            total_market_value += position.market_value
            total_unrealized_pnl += position.unrealized_pnl
            total_realized_pnl += position.realized_pnl

        return {
            'total_positions': len(positions),
            'total_market_value': total_market_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': total_realized_pnl,
            'total_pnl': total_unrealized_pnl + total_realized_pnl,
            'positions': positions,
        }

    async def get_exposure_by_instrument(self, strategy_id: UUID) -> dict[str, Decimal]:
        """
        Get portfolio exposure broken down by instrument.

        Args:
            strategy_id: Strategy UUID

        Returns:
            Dictionary mapping instrument to market value
        """
        positions = await self.find_by_strategy(strategy_id, include_closed=False)

        exposure = {}
        for position in positions:
            exposure[position.instrument] = position.market_value

        return exposure

    async def count(self, strategy_id: UUID | None = None, include_closed: bool = False) -> int:
        """
        Count positions with optional filters.

        Args:
            strategy_id: Optional strategy filter
            include_closed: Include closed positions

        Returns:
            Number of matching positions
        """
        query_filter: dict[str, Any] = {}

        if strategy_id:
            query_filter['strategy_id'] = strategy_id
        if not include_closed:
            query_filter['quantity'] = {'$ne': 0}

        return await PortfolioPosition.find(query_filter).count()

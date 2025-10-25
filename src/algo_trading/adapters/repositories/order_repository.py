"""
Order Repository - Hexagonal Architecture Adapter.

Provides data access operations for trade orders with audit trail.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.algo_trading.adapters.models.order import OrderStatus, TradeOrder


class OrderRepository:
    """
    Repository for trade order persistence with audit trail.

    Implements outbound port for order data access.
    Maintains immutable audit trail for all order state changes.
    """

    async def create_order(
        self,
        strategy_id: UUID,
        session_id: UUID,
        instrument: str,
        side: str,
        quantity: int,
        order_type: str,
        limit_price: Decimal | None = None,
        correlation_id: str | None = None,
    ) -> TradeOrder:
        """
        Create a new trade order with audit trail.

        Args:
            strategy_id: Strategy placing the order
            session_id: Trading session ID
            instrument: Trading instrument (e.g., "AAPL", "SBER")
            side: Order side ("buy" or "sell")
            quantity: Number of units
            order_type: Order type ("market", "limit", "stop_loss")
            limit_price: Limit price for limit orders
            correlation_id: Correlation ID for tracking

        Returns:
            Created order with PENDING status

        Note:
            All order state changes are immutable once persisted.
        """
        order = TradeOrder(
            strategy_id=strategy_id,
            session_id=session_id,
            instrument=instrument,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            correlation_id=correlation_id,
            status=OrderStatus.PENDING,
        )

        await order.insert()
        return order

    async def find_by_id(self, order_id: UUID) -> TradeOrder | None:
        """
        Find order by ID.

        Args:
            order_id: Order UUID

        Returns:
            Order if found, None otherwise
        """
        return await TradeOrder.find_one(TradeOrder.order_id == order_id)

    async def find_by_strategy(
        self,
        strategy_id: UUID,
        status: OrderStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TradeOrder]:
        """
        Find orders for a strategy.

        Args:
            strategy_id: Strategy UUID
            status: Optional status filter
            limit: Maximum results
            offset: Skip N results

        Returns:
            List of orders sorted by creation time (newest first)
        """
        query = TradeOrder.find(TradeOrder.strategy_id == strategy_id)

        if status:
            query = query.find(TradeOrder.status == status)

        return await query.sort("-created_at").skip(offset).limit(limit).to_list()

    async def find_by_session(
        self,
        session_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TradeOrder]:
        """
        Find orders for a trading session.

        Args:
            session_id: Session UUID
            limit: Maximum results
            offset: Skip N results

        Returns:
            List of orders sorted by creation time
        """
        return (
            await TradeOrder.find(TradeOrder.session_id == session_id)
            .sort("-created_at")
            .skip(offset)
            .limit(limit)
            .to_list()
        )

    async def find_active_orders(
        self,
        strategy_id: UUID | None = None,
    ) -> list[TradeOrder]:
        """
        Find all active (non-terminal) orders.

        Args:
            strategy_id: Optional strategy filter

        Returns:
            List of orders with PENDING or SUBMITTED status
        """
        query = TradeOrder.find(
            {"status": {"$in": [OrderStatus.PENDING, OrderStatus.SUBMITTED]}}
        )

        if strategy_id:
            query = query.find(TradeOrder.strategy_id == strategy_id)

        return await query.sort("created_at").to_list()

    async def update_status(
        self,
        order_id: UUID,
        new_status: OrderStatus,
        filled_quantity: int | None = None,
        filled_price: Decimal | None = None,
        rejection_reason: str | None = None,
    ) -> TradeOrder:
        """
        Update order status with audit trail.

        Args:
            order_id: Order UUID
            new_status: New status
            filled_quantity: Filled quantity (for FILLED/PARTIALLY_FILLED)
            filled_price: Execution price
            rejection_reason: Reason for rejection

        Returns:
            Updated order

        Raises:
            ValueError: If order not found
            ValueError: If invalid status transition

        Note:
            Status transitions are validated:
            - PENDING → SUBMITTED, CANCELLED, REJECTED
            - SUBMITTED → FILLED, PARTIALLY_FILLED, CANCELLED, REJECTED
            - PARTIALLY_FILLED → FILLED, CANCELLED
        """
        order = await self.find_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Validate status transition
        valid_transitions = {
            OrderStatus.PENDING: {
                OrderStatus.SUBMITTED,
                OrderStatus.CANCELLED,
                OrderStatus.REJECTED,
            },
            OrderStatus.SUBMITTED: {
                OrderStatus.FILLED,
                OrderStatus.PARTIALLY_FILLED,
                OrderStatus.CANCELLED,
                OrderStatus.REJECTED,
            },
            OrderStatus.PARTIALLY_FILLED: {
                OrderStatus.FILLED,
                OrderStatus.CANCELLED,
            },
        }

        if new_status not in valid_transitions.get(order.status, set()):
            # Allow idempotent updates
            if new_status == order.status:
                return order

            raise ValueError(
                f"Invalid status transition from {order.status} to {new_status}"
            )

        # Update order
        order.status = new_status

        if new_status in {OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED}:
            if filled_quantity is not None:
                order.filled_quantity = Decimal(str(filled_quantity))
            if filled_price is not None:
                order.filled_price = filled_price
            order.filled_at = datetime.utcnow()

        if new_status == OrderStatus.REJECTED and rejection_reason:
            order.rejection_reason = rejection_reason

        if new_status == OrderStatus.CANCELLED:
            order.cancelled_at = datetime.utcnow()

        order.updated_at = datetime.utcnow()

        await order.save()
        return order

    async def cancel_order(self, order_id: UUID) -> TradeOrder:
        """
        Cancel an order.

        Args:
            order_id: Order UUID

        Returns:
            Cancelled order

        Raises:
            ValueError: If order cannot be cancelled
        """
        return await self.update_status(order_id, OrderStatus.CANCELLED)

    async def get_order_statistics(
        self,
        strategy_id: UUID,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> dict:
        """
        Get order statistics for a strategy.

        Args:
            strategy_id: Strategy UUID
            period_start: Optional period start
            period_end: Optional period end

        Returns:
            Dictionary with order statistics:
            - total_orders: Total number of orders
            - filled_orders: Number of filled orders
            - cancelled_orders: Number of cancelled orders
            - rejected_orders: Number of rejected orders
            - total_volume: Total trading volume
            - average_fill_price: Average fill price
        """
        query_filter: dict[str, Any] = {"strategy_id": strategy_id}

        if period_start or period_end:
            date_filter: dict[str, datetime] = {}
            if period_start:
                date_filter["$gte"] = period_start
            if period_end:
                date_filter["$lte"] = period_end
            query_filter["created_at"] = date_filter

        orders = await TradeOrder.find(query_filter).to_list()

        filled_orders = [o for o in orders if o.status == OrderStatus.FILLED]
        total_volume = sum(o.filled_quantity for o in filled_orders if o.filled_quantity)
        filled_prices = [
            o.filled_price for o in filled_orders if o.filled_price is not None
        ]

        return {
            "total_orders": len(orders),
            "filled_orders": len(filled_orders),
            "cancelled_orders": sum(
                1 for o in orders if o.status == OrderStatus.CANCELLED
            ),
            "rejected_orders": sum(
                1 for o in orders if o.status == OrderStatus.REJECTED
            ),
            "total_volume": total_volume,
            "average_fill_price": (
                sum(filled_prices, Decimal("0")) / len(filled_prices)
                if filled_prices
                else Decimal("0")
            ),
        }

    async def count(
        self,
        strategy_id: UUID | None = None,
        status: OrderStatus | None = None,
    ) -> int:
        """
        Count orders with optional filters.

        Args:
            strategy_id: Optional strategy filter
            status: Optional status filter

        Returns:
            Number of matching orders
        """
        query_filter: dict[str, Any] = {}

        if strategy_id:
            query_filter["strategy_id"] = strategy_id
        if status:
            query_filter["status"] = status

        return await TradeOrder.find(query_filter).count()

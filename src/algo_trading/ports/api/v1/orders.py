"""
Orders API endpoints - Hexagonal Architecture Inbound Port.

REST API endpoints for managing trade orders.
Following FastAPI patterns and RFC7807 error handling.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.algo_trading.adapters.models.order import OrderStatus, TradeOrder

orders_router = APIRouter(prefix='/api/v1/orders', tags=['Trade Orders'])



class OrderListResponseSchema(BaseModel):
    """Response schema for listing orders."""

    orders: list[TradeOrder] = Field(description='List of trade orders')
    total: int = Field(ge=0, description='Total number of orders matching filters')
    limit: int = Field(ge=1, le=100, description='Request limit parameter')
    offset: int = Field(ge=0, description='Request offset parameter')


@orders_router.get(
    '/',
    response_model=OrderListResponseSchema,
    summary='List trade orders',
    description='Retrieve trade orders with optional filtering by strategy, status, or date range',
)
async def list_orders(
    strategy_id: UUID | None = Query(None, description='Filter orders by strategy ID'),
    status_filter: OrderStatus | None = Query(None, alias='status', description='Filter orders by status'),
    from_date: datetime | None = Query(None, description='Filter orders from this date'),
    to_date: datetime | None = Query(None, description='Filter orders until this date'),
    limit: int = Query(50, ge=1, le=100, description='Maximum number of orders to return'),
    offset: int = Query(0, ge=0, description='Number of orders to skip'),
) -> OrderListResponseSchema:
    """
    List trade orders with filtering and pagination (T049).

    Args:
        strategy_id: Optional filter by strategy
        status_filter: Optional filter by order status
        from_date: Optional filter by start date
        to_date: Optional filter by end date
        limit: Maximum number of orders to return
        offset: Number of orders to skip for pagination

    Returns:
        Paginated list of orders with total count

    Raises:
        HTTPException 422: Invalid query parameters
        HTTPException 500: Internal server error
    """

    query: dict[str, Any] = {}

    if strategy_id:
        query['strategy_id'] = strategy_id

    if status_filter:
        query['status'] = status_filter

    # TODO: Add date range filtering
    # TODO: Implement proper filtering with Beanie query builder

    all_orders = await TradeOrder.find_all().to_list()

    # Apply filters
    filtered_orders = all_orders
    if strategy_id:
        filtered_orders = [o for o in filtered_orders if o.strategy_id == strategy_id]
    if status_filter:
        filtered_orders = [o for o in filtered_orders if o.status == status_filter]
    if from_date:
        filtered_orders = [o for o in filtered_orders if o.submitted_at >= from_date]
    if to_date:
        filtered_orders = [o for o in filtered_orders if o.submitted_at <= to_date]

    total = len(filtered_orders)

    # Apply pagination
    paginated_orders = filtered_orders[offset : offset + limit]

    return OrderListResponseSchema(orders=paginated_orders, total=total, limit=limit, offset=offset)


@orders_router.get(
    '/{order_id}',
    response_model=TradeOrder,
    summary='Get order details',
    description='Retrieve detailed information about a specific trade order',
)
async def get_order(order_id: UUID) -> TradeOrder:
    """
    Get order by ID (T050).

    Args:
        order_id: Unique order identifier

    Returns:
        Order details

    Raises:
        HTTPException 404: Order not found
        HTTPException 500: Internal server error
    """
    order = await TradeOrder.find_one(TradeOrder.order_id == order_id)

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Order {order_id} not found')

    return order


@orders_router.post(
    '/{order_id}/cancel',
    response_model=TradeOrder,
    summary='Cancel trade order',
    description='Cancel a pending or submitted trade order',
)
async def cancel_order(order_id: UUID) -> TradeOrder:
    """
    Cancel a trade order (T051).

    Args:
        order_id: Unique order identifier

    Returns:
        Cancelled order

    Raises:
        HTTPException 404: Order not found
        HTTPException 409: Order cannot be cancelled (already filled or rejected)
        HTTPException 500: Internal server error
    """
    order = await TradeOrder.find_one(TradeOrder.order_id == order_id)

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Order {order_id} not found')

    # Check if order can be cancelled
    if order.status in [OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Order cannot be cancelled. Current status: {order.status}',
        )

    # Update order status to cancelled
    try:
        order.update_status(OrderStatus.CANCELLED)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    # TODO: Call OrderExecutor service to cancel order with broker
    await order.save()

    return order

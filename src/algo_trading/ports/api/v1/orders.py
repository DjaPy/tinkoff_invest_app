"""
Orders API endpoints - Hexagonal Architecture Inbound Port.

REST API endpoints for managing trade orders.
Following FastAPI patterns and RFC7807 error handling.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.algo_trading.ports.api.v1.schemas.orders_schema import (
    OrderListResponseSchema,
    OrderResponseSchema,
)
from src.users.services.auth import get_current_active_user
from src.algo_trading.enums import OrderStatusEnum
from src.algo_trading.adapters.repositories.order_repository import OrderRepository
from src.algo_trading.services.order_executor import OrderExecutor

orders_router = APIRouter(
    prefix='/api/v1/orders',
    tags=['Trade Orders'],
    dependencies=[Depends(get_current_active_user)],
)


@orders_router.get(
    '/',
    response_model=OrderListResponseSchema,
    summary='List trade orders',
    description='Retrieve trade orders with optional filtering by strategy, status, or date range',
)
async def list_orders(
    strategy_id: UUID | None = Query(None, description='Filter orders by strategy ID'),
    status_filter: OrderStatusEnum | None = Query(None, alias='status', description='Filter orders by status'),
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
    repository = OrderRepository()
    orders, total = await repository.find_with_filters(
        strategy_id=strategy_id,
        status=status_filter,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )

    resp_orders = [OrderResponseSchema(**order.model_dump())for order in orders]

    return OrderListResponseSchema(orders=resp_orders, total=total, limit=limit, offset=offset)


@orders_router.get(
    '/{order_id}',
    response_model=OrderResponseSchema,
    summary='Get order details',
    description='Retrieve detailed information about a specific trade order',
)
async def get_order(order_id: UUID) -> OrderResponseSchema:
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
    repository = OrderRepository()
    order = await repository.find_by_id(order_id)

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Order {order_id} not found')

    return order


@orders_router.post(
    '/{order_id}/cancel',
    response_model=OrderResponseSchema,
    summary='Cancel trade order',
    description='Cancel a pending or submitted trade order',
)
async def cancel_order(order_id: UUID) -> OrderResponseSchema:
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
    repository = OrderRepository()
    order = await repository.find_by_id(order_id)

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Order {order_id} not found')

    if order.status in [OrderStatusEnum.FILLED, OrderStatusEnum.REJECTED, OrderStatusEnum.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Order cannot be cancelled. Current status: {order.status}',
        )

    executor = OrderExecutor()
    try:
        cancelled_order = await executor.cancel_order(order_id)
        return OrderResponseSchema(**cancelled_order.model_dump(exclude={'id'}))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

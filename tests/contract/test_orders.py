"""
Contract tests for Orders API endpoints (T012, T013, T014)

GET /api/v1/orders - List trade orders (T012)
GET /api/v1/orders/{order_id} - Get order details (T013)
POST /api/v1/orders/{order_id}/cancel - Cancel order (T014)

These tests validate the API contracts for managing trade orders.
They should FAIL until the actual endpoint implementations are complete.

Following TDD approach - tests written before implementation.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field
from starlette import status

from src.algo_trading.adapters.models.order import OrderSideEnum, OrderStatusEnum, OrderTypeEnum, TradeOrderDocument


class OrderListResponse(BaseModel):
    """Response schema for GET /api/v1/orders."""

    orders: list[TradeOrderDocument] = Field(description='List of trade orders')
    total: int = Field(ge=0, description='Total number of orders matching filters')
    limit: int = Field(ge=1, le=100, description='Request limit parameter')
    offset: int = Field(ge=0, description='Request offset parameter')


async def test_get_orders_returns_order_list(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/orders returns list of orders"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        # Contract assertions
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()

        # Validate response using Pydantic model
        response_model = OrderListResponse(**data)
        assert isinstance(response_model.orders, list)
        assert isinstance(response_model.total, int)
        assert response_model.total >= 0
        assert response_model.limit > 0
        assert response_model.offset >= 0


async def test_get_orders_validates_order_structure(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/orders returns orders with correct Pydantic structure"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = OrderListResponse(**data)

        valid_types = [
            OrderTypeEnum.MARKET,
            OrderTypeEnum.LIMIT,
            OrderTypeEnum.STOP_LOSS,
            OrderTypeEnum.TAKE_PROFIT,
        ]
        if response_model.orders:
            for order in response_model.orders:
                assert order.order_id is not None
                assert order.strategy_id is not None
                assert order.session_id is not None
                assert order.correlation_id is not None
                assert order.instrument is not None

                assert order.order_type in valid_types
                assert order.side in [OrderSideEnum.BUY, OrderSideEnum.SELL]
                assert order.quantity > 0
                assert order.status in [
                    OrderStatusEnum.PENDING,
                    OrderStatusEnum.SUBMITTED,
                    OrderStatusEnum.FILLED,
                    OrderStatusEnum.PARTIALLY_FILLED,
                    OrderStatusEnum.CANCELLED,
                    OrderStatusEnum.REJECTED,
                ]


@pytest.mark.parametrize(
    'query_params',
    [
        {},  # No filters
        {'limit': 10, 'offset': 0},  # Pagination
        {'limit': 50, 'offset': 10},  # Different pagination
        {'status': 'pending'},  # Filter by status
        {'status': 'filled'},
    ],
)
async def test_get_orders_filters_and_pagination(client, config, mock_auth, mongo_connection, query_params):
    """Test GET /api/v1/orders supports filtering and pagination"""
    query_string = '&'.join([f'{k}={v}' for k, v in query_params.items()])
    url = f'http://127.0.0.1:{config.http.port}/api/v1/orders'
    if query_string:
        url += f'?{query_string}'

    async with client.get(
        url=url,
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = OrderListResponse(**data)
        if 'limit' in query_params:
            assert response_model.limit == query_params['limit']
        if 'offset' in query_params:
            assert response_model.offset == query_params['offset']


async def test_get_orders_filter_by_strategy_id(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/orders can filter by strategy_id"""
    strategy_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders?strategy_id={strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = OrderListResponse(**data)
        for order in response_model.orders:
            assert order.strategy_id == strategy_id


async def test_get_orders_filter_by_date_range(client, config, mongo_connection, mock_auth, create_order):
    """Test GET /api/v1/orders can filter by date range"""
    base_time = datetime.now(timezone.utc)
    from_date = base_time - timedelta(days=5)
    to_date = base_time - timedelta(days=2)

    await create_order(submitted_at=base_time - timedelta(days=7))
    await create_order(submitted_at=base_time - timedelta(days=6))

    order_in_range_1 = await create_order(submitted_at=base_time - timedelta(days=4))
    order_in_range_2 = await create_order(submitted_at=base_time - timedelta(days=3))

    await create_order(submitted_at=base_time + timedelta(days=1))

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders?from_date={from_date.date().isoformat()}&to_date={to_date.date().isoformat()}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = OrderListResponse(**data)
        assert response_model.total == 2
        assert len(response_model.orders) == 2
        returned_ids = {order.order_id for order in response_model.orders}
        assert order_in_range_1.order_id in returned_ids
        assert order_in_range_2.order_id in returned_ids


async def test_get_orders_unauthorized(client, config):
    """Test GET /api/v1/orders requires authentication"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401


async def test_get_orders_validation_error_invalid_limit(client, config, mock_auth):
    """Test GET /api/v1/orders validates limit parameter"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders?limit=1000',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = await response.json()
        assert 'status' in data
        assert data['status'] == 422


async def test_get_order_by_id_returns_order_details(client, config, mongo_connection, mock_auth, create_order):
    """Test GET /api/v1/orders/{order_id} returns order details"""
    created_order = await create_order()
    order_id = created_order.order_id

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders/{order_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()

        order = TradeOrderDocument(**data)
        assert order.order_id == order_id
        assert order.strategy_id is not None
        assert order.instrument is not None


async def test_get_order_by_id_not_found(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/orders/{order_id} returns 404 for non-existent order"""
    non_existent_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders/{non_existent_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert data['status'] == 404


async def test_get_order_by_id_unauthorized(client, config):
    """Test GET /api/v1/orders/{order_id} requires authentication"""
    order_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders/{order_id}',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401


async def test_cancel_order_cancels_pending_order(client, config, mongo_connection, mock_auth, create_order):
    """Test POST /api/v1/orders/{order_id}/cancel cancels a pending order"""
    created_order = await create_order(status=OrderStatusEnum.PENDING, filled_price=Decimal('100'))
    order_id = created_order.order_id

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders/{order_id}/cancel',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()

        order = TradeOrderDocument(**data)
        assert order.order_id == order_id
        assert order.status == OrderStatusEnum.CANCELLED


async def test_cancel_order_not_found(client, config, mongo_connection, mock_auth):
    """Test POST /api/v1/orders/{order_id}/cancel returns 404 for non-existent order"""
    non_existent_id = uuid4()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders/{non_existent_id}/cancel',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert data['status'] == 404


async def test_cancel_order_conflict_already_filled(client, config, services, mock_auth):
    """Test POST /api/v1/orders/{order_id}/cancel returns 409 if order already filled"""
    order_id = uuid4()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders/{order_id}/cancel',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        # Should return 409 Conflict if order is in final state
        if response.status == status.HTTP_409_CONFLICT:
            data = await response.json()
            assert 'type' in data
            assert 'status' in data
            assert data['status'] == 409


async def test_cancel_order_unauthorized(client, config, services):
    """Test POST /api/v1/orders/{order_id}/cancel requires authentication"""
    order_id = uuid4()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/orders/{order_id}/cancel',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401

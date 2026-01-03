"""
Contract tests for Positions API endpoints (T015)

GET /api/v1/positions - List portfolio positions
GET /api/v1/positions/{position_id} - Get position details

These tests validate the API contracts for managing portfolio positions.
They should FAIL until the actual endpoint implementations are complete.

Following TDD approach - tests written before implementation.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field
from starlette import status

from src.algo_trading.adapters.models.position import PortfolioPositionDocument


class PositionListResponse(BaseModel):
    """Response schema for GET /api/v1/positions."""

    positions: list[PortfolioPositionDocument] = Field(description='List of portfolio positions')
    total_value: Decimal = Field(ge=0, description='Total portfolio market value')
    total_pnl: Decimal = Field(description='Total unrealized P&L')


@pytest.mark.asyncio
async def test_get_positions_returns_position_list(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/positions returns list of positions"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()

        response_model = PositionListResponse(**data)
        assert isinstance(response_model.positions, list)
        assert isinstance(response_model.total_value, Decimal)
        assert isinstance(response_model.total_pnl, Decimal)
        assert response_model.total_value >= 0


@pytest.mark.asyncio
async def test_get_positions_validates_position_structure(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/positions returns positions with correct Pydantic structure"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = PositionListResponse(**data)

        if response_model.positions:
            for position in response_model.positions:
                assert position.position_id is not None
                assert position.strategy_id is not None
                assert position.instrument is not None
                assert position.quantity is not None
                assert position.average_price > 0
                assert position.current_price > 0
                assert position.updated_at is not None
                # Computed fields
                assert position.unrealized_pnl is not None
                assert position.market_value >= 0
                assert position.pnl_percent is not None


@pytest.mark.asyncio
async def test_get_positions_empty_list(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/positions returns empty list when no positions"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = PositionListResponse(**data)
        # Could be empty or have positions
        if not response_model.positions:
            assert response_model.total_value == 0
            assert response_model.total_pnl == 0


@pytest.mark.asyncio
async def test_get_positions_filter_by_strategy_id(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/positions can filter by strategy_id"""
    strategy_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions?strategy_id={strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = PositionListResponse(**data)
        for position in response_model.positions:
            assert position.strategy_id == strategy_id


@pytest.mark.asyncio
async def test_get_positions_filter_by_instrument(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/positions can filter by instrument"""
    instrument = 'AAPL'

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions?instrument={instrument}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = PositionListResponse(**data)
        for position in response_model.positions:
            assert position.instrument == instrument


@pytest.mark.asyncio
async def test_get_positions_calculates_totals_correctly(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/positions calculates total_value and total_pnl correctly"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        response_model = PositionListResponse(**data)

        if response_model.positions:
            calculated_value = sum(pos.market_value for pos in response_model.positions)
            calculated_pnl = sum(pos.unrealized_pnl for pos in response_model.positions)

            assert response_model.total_value == calculated_value
            assert response_model.total_pnl == calculated_pnl


@pytest.mark.asyncio
async def test_get_positions_unauthorized(client, config):
    """Test GET /api/v1/positions requires authentication"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401


@pytest.mark.asyncio
async def test_get_position_by_id_returns_position_details(
        client, config, mongo_connection, mock_auth, create_position,
):
    """Test GET /api/v1/positions/{position_id} returns position details"""
    created_position = await create_position()
    position_id = created_position.position_id

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions/{position_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        assert 'application/json' in response.headers['content-type']

        data = await response.json()
        position = PortfolioPositionDocument(**data)
        assert position.position_id == position_id
        assert position.strategy_id is not None
        assert position.instrument is not None
        assert position.quantity is not None
        assert position.average_price > 0
        assert position.current_price > 0


@pytest.mark.asyncio
async def test_get_position_by_id_includes_computed_fields(client, config, mock_auth, create_position):
    """Test GET /api/v1/positions/{position_id} includes computed fields"""
    created_position = await create_position()
    position_id = created_position.position_id

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions/{position_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        position = PortfolioPositionDocument(**data)
        assert position.unrealized_pnl is not None
        assert position.market_value is not None
        assert position.pnl_percent is not None

        expected_pnl = (position.current_price - position.average_price) * position.quantity
        assert position.unrealized_pnl == expected_pnl

        expected_value = abs(position.quantity) * position.current_price
        assert position.market_value == expected_value


@pytest.mark.asyncio
async def test_get_position_by_id_not_found(client, config, mongo_connection, mock_auth):
    """Test GET /api/v1/positions/{position_id} returns 404 for non-existent position"""
    non_existent_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions/{non_existent_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert data['status'] == 404


@pytest.mark.asyncio
async def test_get_position_by_id_unauthorized(client, config):
    """Test GET /api/v1/positions/{position_id} requires authentication"""
    position_id = uuid4()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions/{position_id}',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401


@pytest.mark.parametrize('invalid_id', ['not-a-uuid', '12345', 'invalid-format'])
@pytest.mark.asyncio
async def test_get_position_by_id_invalid_uuid_format(client, config, mongo_connection, mock_auth, invalid_id):
    """Test GET /api/v1/positions/{position_id} validates UUID format"""
    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/positions/{invalid_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_CONTENT]
        data = await response.json()
        assert 'invalid_params' in data
        assert 'status' in data

"""
Contract test for DELETE /api/v1/strategies/{strategy_id} endpoint (T008)

This test validates the API contract for deleting trading strategies.
It should FAIL until the actual endpoint implementation is complete.

Following TDD approach - tests written before implementation.
"""

from uuid import uuid4

import pytest
from starlette import status

from src.algo_trading.enums import StrategyStatusEnum


async def test_delete_strategy_removes_existing_strategy(
        client, config, mongo_connection, mock_auth, create_trading_strategy,
):
    """Test DELETE /api/v1/strategies/{strategy_id} successfully deletes a strategy"""
    strategy = await create_trading_strategy(status=StrategyStatusEnum.INACTIVE)

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy.strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_204_NO_CONTENT
        content = await response.text()
        assert content == '' or content is None



async def test_delete_strategy_not_found(client, config, mongo_connection, mock_auth):
    """Test DELETE /api/v1/strategies/{strategy_id} returns 404 for non-existent strategy"""
    non_existent_id = uuid4()

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{non_existent_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        assert 'detail' in data
        assert 'title' in data
        assert 'status' in data
        assert data['status'] == 404



async def test_delete_strategy_unauthorized_without_token(client, config, mongo_connection):
    """Test DELETE /api/v1/strategies/{strategy_id} requires authentication (401)"""
    strategy_id = uuid4()

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401
        assert data['title'] == 'Unauthorized'



async def test_delete_active_strategy_returns_conflict(client, config, mongo_connection):
    """Test DELETE /api/v1/strategies/{strategy_id} returns 409 for active strategy"""
    active_strategy_id = uuid4()

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{active_strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        if response.status == status.HTTP_409_CONFLICT:
            data = await response.json()
            assert 'detail' in data
            assert 'title' in data
            assert 'status' in data
            assert data['status'] == 409
            assert 'active' in data.get('detail', '').lower() or 'cannot delete' in data.get('detail', '').lower()



async def test_delete_strategy_idempotent(client, config, mongo_connection, mock_auth):
    """Test DELETE /api/v1/strategies/{strategy_id} is idempotent (deleting twice)"""
    strategy_id = uuid4()

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        pass

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND



async def test_delete_strategy_handles_internal_error(client, config):
    """Test DELETE /api/v1/strategies/{strategy_id} handles internal server errors (500)"""
    strategy_id = uuid4()

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        if response.status == status.HTTP_500_INTERNAL_SERVER_ERROR:
            data = await response.json()
            assert 'type' in data
            assert 'title' in data
            assert 'status' in data
            assert data['status'] == 500


@pytest.mark.parametrize('invalid_id', ['not-a-uuid', '12345', 'invalid-format'])
async def test_delete_strategy_invalid_uuid_format(client, config, mock_auth, invalid_id):
    """Test DELETE /api/v1/strategies/{strategy_id} validates UUID format"""
    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{invalid_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_CONTENT]
        data = await response.json()
        assert 'invalid_params' in data
        assert 'status' in data
        assert data['status'] == status.HTTP_422_UNPROCESSABLE_CONTENT

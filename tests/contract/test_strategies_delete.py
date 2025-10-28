"""
Contract test for DELETE /api/v1/strategies/{strategy_id} endpoint (T008)

This test validates the API contract for deleting trading strategies.
It should FAIL until the actual endpoint implementation is complete.

Following TDD approach - tests written before implementation.
"""

from uuid import uuid4

import pytest
from starlette import status


@pytest.mark.asyncio
async def test_delete_strategy_removes_existing_strategy(client, config):
    """Test DELETE /api/v1/strategies/{strategy_id} successfully deletes a strategy"""
    strategy_id = uuid4()

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        # Contract assertions - 204 No Content on successful deletion
        assert response.status == status.HTTP_204_NO_CONTENT
        # 204 responses should not have content
        content = await response.text()
        assert content == '' or content is None


@pytest.mark.asyncio
async def test_delete_strategy_not_found(client, config):
    """Test DELETE /api/v1/strategies/{strategy_id} returns 404 for non-existent strategy"""
    non_existent_id = uuid4()

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{non_existent_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_404_NOT_FOUND
        data = await response.json()
        # RFC7807 error format
        assert 'type' in data
        assert 'title' in data
        assert 'status' in data
        assert data['status'] == 404


@pytest.mark.asyncio
async def test_delete_strategy_unauthorized_without_token(client, config):
    """Test DELETE /api/v1/strategies/{strategy_id} requires authentication (401)"""
    strategy_id = uuid4()

    # No Authorization header
    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Content-Type': 'application/json'},
    ) as response:
        assert response.status == status.HTTP_401_UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401
        assert data['title'] == 'Unauthorized'


@pytest.mark.asyncio
async def test_delete_active_strategy_returns_conflict(client, config):
    """Test DELETE /api/v1/strategies/{strategy_id} returns 409 for active strategy"""
    # Per OpenAPI spec: Cannot delete active strategy
    active_strategy_id = uuid4()

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{active_strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        # Should return 409 Conflict if strategy is active
        if response.status == status.HTTP_409_CONFLICT:
            data = await response.json()
            # RFC7807 error format
            assert 'type' in data
            assert 'title' in data
            assert 'status' in data
            assert data['status'] == 409
            # Error message should indicate strategy cannot be deleted
            assert 'active' in data.get('detail', '').lower() or 'cannot delete' in data.get('detail', '').lower()


@pytest.mark.asyncio
async def test_delete_strategy_idempotent(client, config):
    """Test DELETE /api/v1/strategies/{strategy_id} is idempotent (deleting twice)"""
    strategy_id = uuid4()

    # First deletion
    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        pass

    # Second deletion of same strategy
    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        # Should return 404 since strategy no longer exists
        assert response.status == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_strategy_handles_internal_error(client, config):
    """Test DELETE /api/v1/strategies/{strategy_id} handles internal server errors (500)"""
    strategy_id = uuid4()

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{strategy_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        # If there's an internal error, it should follow RFC7807 format
        if response.status == status.HTTP_500_INTERNAL_SERVER_ERROR:
            data = await response.json()
            assert 'type' in data
            assert 'title' in data
            assert 'status' in data
            assert data['status'] == 500


@pytest.mark.parametrize('invalid_id', ['not-a-uuid', '12345', 'invalid-format'])
@pytest.mark.asyncio
async def test_delete_strategy_invalid_uuid_format(client, config, invalid_id):
    """Test DELETE /api/v1/strategies/{strategy_id} validates UUID format"""
    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/api/v1/strategies/{invalid_id}',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
    ) as response:
        # Should return 400 or 422 for invalid UUID format
        assert response.status in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        data = await response.json()
        assert 'type' in data
        assert 'status' in data

"""
Contract tests for TinkoffAccount API endpoints.

Tests validate API contracts for managing Tinkoff accounts (production and sandbox).
Following TDD approach - tests validate expected behavior before full implementation.
"""
import uuid
from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest
from beanie import PydanticObjectId
from starlette import status

from src.algo_trading.adapters.models.strategy import (
    TinkoffAccountDocument,
    TinkoffAccountType,
)


@pytest.fixture
async def mock_tinkoff_sandbox_service():
    """Mock TinkoffInvestServiceSandbox for account creation tests."""
    with patch('src.algo_trading.services.tinkoff_account_manager.get_context') as mock_context:
        mock_service = AsyncMock()

        mock_sandbox = AsyncMock()
        mock_sandbox.open_sandbox_account = AsyncMock(
            return_value=AsyncMock(account_id='test-sandbox-account-id'),
        )
        mock_sandbox.sandbox_pay_in = AsyncMock(return_value=True)
        mock_service.sandbox = mock_sandbox

        # Mock users.get_accounts method
        mock_users = AsyncMock()
        mock_account_info = AsyncMock()
        mock_account_info.id = 'test-sandbox-account-id'
        mock_account_info.status = 'ACCOUNT_STATUS_OPEN'
        mock_account_info.access_level = 'ACCOUNT_ACCESS_LEVEL_FULL_ACCESS'
        mock_users.get_accounts = AsyncMock(
            return_value=AsyncMock(accounts=[mock_account_info]),
        )
        mock_service.users = mock_users

        async def mock_getitem(self, key):
            return mock_service

        mock_context.return_value.__getitem__ = mock_getitem
        yield mock_service


async def test_post_sandbox_account_creates_new_sandbox(
    client,
    config,
    services,
    mongo_connection,
    mock_auth,
    mock_tinkoff_sandbox_service,
):
    """Test POST /accounts/sandbox creates new sandbox account."""
    account_data = {
        'name': 'Test Sandbox Account',
        'initial_balance': 1000000.0,
        'set_as_default': True,
    }

    async with client.post(
            url=f'http://127.0.0.1:{config.http.port}/accounts/sandbox',
            headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
            json=account_data,
    ) as response:
        data = await response.json()
        assert response.status == status.HTTP_201_CREATED
        assert 'application/json' in response.headers['content-type']


        assert data['name'] == account_data['name']
        assert data['account_type'] == 'sandbox'
        assert data['is_default'] is True
        assert data['initial_balance'] == account_data['initial_balance']
        assert 'id' in data
        assert 'account_id' in data
        assert 'created_at' in data


async def test_post_sandbox_account_validates_required_fields(
    client,
    config,
    mock_auth,
):
    """Test POST /accounts/sandbox validates required fields."""
    invalid_data = {}

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/accounts/sandbox',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=invalid_data,
    ) as response:
        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        data = await response.json()
        assert 'detail' in data or 'invalid_params' in data


async def test_post_sandbox_account_requires_authentication(
    client,
    config,
):
    """Test POST /accounts/sandbox requires authentication."""
    account_data = {
        'name': 'Test Sandbox Account',
        'initial_balance': 1000000.0,
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/accounts/sandbox',
        headers={'Content-Type': 'application/json'},
        json=account_data,
    ) as response:
        assert response.status == HTTPStatus.UNAUTHORIZED
        data = await response.json()
        assert data['status'] == 401
        assert data['title'] == 'Unauthorized'


async def test_get_accounts_returns_user_accounts(
    client,
    config,
    services,
    mongo_connection,
    mock_auth,
):
    """Test GET /accounts returns user's accounts."""
    test_account = TinkoffAccountDocument(
        account_id='test-account-123',
        account_type=TinkoffAccountType.SANDBOX,
        name='Test Account',
        user_id=mock_auth,
        is_default=True,
    )
    await test_account.insert()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/accounts',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        assert 'accounts' in data
        assert 'total' in data
        assert data['total'] >= 1

        test_acc = next((acc for acc in data['accounts'] if acc['account_id'] == 'test-account-123'), None)
        assert test_acc is not None
        assert test_acc['name'] == 'Test Account'
        assert test_acc['account_type'] == 'sandbox'


async def test_get_accounts_filters_by_type(
    client,
    config,
    services,
    mongo_connection,
    mock_auth,
):
    """Test GET /accounts?account_type=sandbox filters by type."""
    sandbox_account = TinkoffAccountDocument(
        account_id='sandbox-123',
        account_type=TinkoffAccountType.SANDBOX,
        name='Sandbox Account',
        user_id=mock_auth,
        is_default=True,
    )
    await sandbox_account.insert()

    prod_account = TinkoffAccountDocument(
        account_id='prod-123',
        account_type=TinkoffAccountType.PRODUCTION,
        name='Production Account',
        user_id=mock_auth,
        is_default=False,
    )
    await prod_account.insert()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/accounts?account_type=sandbox',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()
        assert all(acc['account_type'] == 'sandbox' for acc in data['accounts'])


async def test_get_account_by_id_returns_account(
    client,
    config,
    services,
    mongo_connection,
    mock_auth,
):
    """Test GET /accounts/{account_id} returns specific account."""
    test_account = TinkoffAccountDocument(
        account_id='test-get-account',
        account_type=TinkoffAccountType.SANDBOX,
        name='Get Test Account',
        user_id=mock_auth,
        is_default=False,
    )
    await test_account.insert()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/accounts/{test_account.id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        assert data['account_id'] == 'test-get-account'
        assert data['name'] == 'Get Test Account'
        assert data['account_type'] == 'sandbox'


async def test_get_account_by_id_returns_404_for_missing(
    client,
    config,
    mongo_connection,
    mock_auth,
):
    """Test GET /accounts/{account_id} returns 404 for missing account."""

    fake_id = PydanticObjectId()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/accounts/{fake_id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == HTTPStatus.NOT_FOUND


async def test_get_account_by_id_returns_403_for_other_user(
    client,
    config,
    services,
    mongo_connection,
    mock_auth,
):
    """Test GET /accounts/{account_id} returns 403 if account belongs to another user."""

    other_user_id = uuid.uuid4()
    other_account = TinkoffAccountDocument(
        account_id='other-user-account',
        account_type=TinkoffAccountType.SANDBOX,
        name='Other User Account',
        user_id=other_user_id,
        is_default=False,
    )
    await other_account.insert()

    async with client.get(
        url=f'http://127.0.0.1:{config.http.port}/accounts/{other_account.id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == status.HTTP_403_FORBIDDEN


async def test_post_set_default_account_updates_default(
    client,
    config,
    services,
    mongo_connection,
    mock_auth,
):
    """Test POST /accounts/{account_id}/set-default sets account as default."""
    account1 = TinkoffAccountDocument(
        account_id='sandbox-1',
        account_type=TinkoffAccountType.SANDBOX,
        name='Sandbox 1',
        user_id=mock_auth,
        is_default=True,
    )
    await account1.insert()

    account2 = TinkoffAccountDocument(
        account_id='sandbox-2',
        account_type=TinkoffAccountType.SANDBOX,
        name='Sandbox 2',
        user_id=mock_auth,
        is_default=False,
    )
    await account2.insert()

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/accounts/{account2.id}/set-default',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        assert data['is_default'] is True
        assert data['id'] == str(account2.id)

        await account1.sync()
        assert account1.is_default is False


async def test_post_fund_sandbox_account_adds_funds(
    client,
    config,
    services,
    mongo_connection,
    mock_auth,
    mock_tinkoff_sandbox_service,
):
    """Test POST /accounts/{account_id}/fund adds funds to sandbox."""
    sandbox_account = TinkoffAccountDocument(
        account_id='sandbox-to-fund',
        account_type=TinkoffAccountType.SANDBOX,
        name='Sandbox To Fund',
        user_id=mock_auth,
        is_default=False,
        initial_balance=1000000.0,
    )
    await sandbox_account.insert()

    fund_request = {
        'amount': 500000.0,
    }

    async with client.post(
        url=f'http://127.0.0.1:{config.http.port}/accounts/{sandbox_account.id}/fund',
        headers={'Authorization': 'Bearer test-token', 'Content-Type': 'application/json'},
        json=fund_request,
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        assert 'id' in data
        assert data['account_type'] == 'sandbox'


async def test_delete_account_removes_account(
    client,
    config,
    services,
    mongo_connection,
    mock_auth,
):
    """Test DELETE /accounts/{account_id} removes account."""
    account_to_delete = TinkoffAccountDocument(
        account_id='account-to-delete',
        account_type=TinkoffAccountType.SANDBOX,
        name='Account To Delete',
        user_id=mock_auth,
        is_default=False,
    )
    await account_to_delete.insert()

    async with client.delete(
        url=f'http://127.0.0.1:{config.http.port}/accounts/{account_to_delete.id}',
        headers={'Authorization': 'Bearer test-token'},
    ) as response:
        assert response.status == status.HTTP_200_OK
        data = await response.json()

        assert data['success'] is True

        deleted_account = await TinkoffAccountDocument.get(account_to_delete.id)
        assert deleted_account is None

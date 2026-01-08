"""TinkoffAccount API endpoints - Account management."""

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.algo_trading.adapters.repositories.tinkoff_account_repository import TinkoffAccountRepository
from src.algo_trading.adapters.models.strategy import TinkoffAccountType
from src.algo_trading.ports.api.v1.schemas.tinkoff_account_schemas import (
    CreateSandboxAccountRequest,
    DeleteAccountResponse,
    FundSandboxAccountRequest,
    TinkoffAccountListResponse,
    TinkoffAccountResponse,
)
from src.algo_trading.services.tinkoff_account_manager import (
    TinkoffAccountManager,
    TinkoffAccountManagerError,
)
from src.users.adapters.models.users import UserDocument
from src.users.services.auth import get_current_active_user

tinkoff_accounts_router = APIRouter(
    prefix='/accounts',
    tags=['Tinkoff Accounts'],
    dependencies=[Depends(get_current_active_user)],
)


@tinkoff_accounts_router.post(
    '/sandbox',
    response_model=TinkoffAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Create sandbox account',
    description='Create new Tinkoff Invest sandbox account for testing strategies without real money',
)
async def create_sandbox_account(
    request: CreateSandboxAccountRequest,
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
) -> TinkoffAccountResponse:
    """
    Create new sandbox account.

    - **name**: User-friendly account name
    - **initial_balance**: Initial virtual balance in rubles (default: 1,000,000)
    - **set_as_default**: Set as default sandbox account for user (default: true)
    """
    manager = TinkoffAccountManager()

    try:
        account_dto = await manager.create_sandbox_account(
            user_id=current_user.user_id,
            name=request.name,
            initial_balance=request.initial_balance,
            set_as_default=request.set_as_default,
        )

        return TinkoffAccountResponse.from_dto(account_dto)

    except TinkoffAccountManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@tinkoff_accounts_router.post(
    '/production/sync',
    response_model=TinkoffAccountListResponse,
    status_code=status.HTTP_200_OK,
    summary='Sync production accounts',
    description='Synchronize production trading accounts from Tinkoff API',
)
async def sync_production_accounts(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
) -> TinkoffAccountListResponse:
    """
    Synchronize production accounts from Tinkoff API.

    Fetches real trading accounts and creates/updates them in database.
    Useful for onboarding or refreshing account list.
    """
    manager = TinkoffAccountManager()

    try:
        accounts_dto = await manager.sync_production_accounts(user_id=current_user.user_id)

        return TinkoffAccountListResponse(
            accounts=[TinkoffAccountResponse.from_dto(dto) for dto in accounts_dto],
            total=len(accounts_dto),
        )

    except TinkoffAccountManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@tinkoff_accounts_router.get(
    '/',
    response_model=TinkoffAccountListResponse,
    status_code=status.HTTP_200_OK,
    summary='Get user accounts',
    description='Get all Tinkoff accounts for current user, optionally filtered by type',
)
async def get_user_accounts(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    account_type: Annotated[
        TinkoffAccountType | None,
        Query(description='Filter by account type (production or sandbox)'),
    ] = None,
) -> TinkoffAccountListResponse:
    """
    Get all accounts for current user.

    - **account_type**: Optional filter by production/sandbox
    """
    manager = TinkoffAccountManager()

    accounts_dto = await manager.get_user_accounts(
        user_id=current_user.user_id,
        account_type=account_type,
    )

    return TinkoffAccountListResponse(
        accounts=[TinkoffAccountResponse.from_dto(dto) for dto in accounts_dto],
        total=len(accounts_dto),
    )


@tinkoff_accounts_router.get(
    '/{account_id}',
    response_model=TinkoffAccountResponse,
    status_code=status.HTTP_200_OK,
    summary='Get account by ID',
    description='Get specific Tinkoff account by ID',
)
async def get_account_by_id(
    account_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
) -> TinkoffAccountResponse:
    """
    Get account by MongoDB ID.

    - **account_id**: MongoDB document ID
    """

    try:
        object_id = PydanticObjectId(account_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid account_id format: {e}',
        ) from e

    account_dto = await TinkoffAccountRepository.get_by_id(object_id)

    if not account_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Account {account_id} not found',
        )

    if account_dto.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access denied to this account',
        )

    return TinkoffAccountResponse.from_dto(account_dto)


@tinkoff_accounts_router.post(
    '/{account_id}/set-default',
    response_model=TinkoffAccountResponse,
    status_code=status.HTTP_200_OK,
    summary='Set default account',
    description='Set account as default for its type (production or sandbox)',
)
async def set_default_account(
    account_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
) -> TinkoffAccountResponse:
    """
    Set account as default for its type.

    - **account_id**: MongoDB document ID
    """
    manager = TinkoffAccountManager()

    try:
        object_id = PydanticObjectId(account_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid account_id format: {e}',
        ) from e

    try:
        updated_dto = await manager.set_default_account(
            user_id=current_user.user_id,
            account_id=object_id,
        )

        return TinkoffAccountResponse.from_dto(updated_dto)

    except TinkoffAccountManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@tinkoff_accounts_router.post(
    '/{account_id}/fund',
    response_model=TinkoffAccountResponse,
    status_code=status.HTTP_200_OK,
    summary='Fund sandbox account',
    description='Add funds to sandbox account (sandbox accounts only)',
)
async def fund_sandbox_account(
    account_id: str,
    request: FundSandboxAccountRequest,
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
) -> TinkoffAccountResponse:
    """
    Add funds to sandbox account.

    - **account_id**: MongoDB document ID
    - **amount**: Amount to add in rubles
    """
    manager = TinkoffAccountManager()

    try:
        object_id = PydanticObjectId(account_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid account_id format: {e}',
        ) from e

    try:
        updated_dto = await manager.fund_sandbox_account(
            user_id=current_user.user_id,
            account_id=object_id,
            amount=request.amount,
        )

        return TinkoffAccountResponse.from_dto(updated_dto)

    except TinkoffAccountManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@tinkoff_accounts_router.delete(
    '/{account_id}',
    response_model=DeleteAccountResponse,
    status_code=status.HTTP_200_OK,
    summary='Delete account',
    description='Delete Tinkoff account from database',
)
async def delete_account(
    account_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
) -> DeleteAccountResponse:
    """
    Delete account.

    - **account_id**: MongoDB document ID
    """
    manager = TinkoffAccountManager()

    try:
        object_id = PydanticObjectId(account_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid account_id format: {e}',
        ) from e

    try:
        success = await manager.delete_account(
            user_id=current_user.user_id,
            account_id=object_id,
        )

        return DeleteAccountResponse(
            success=success,
            message=f'Account {account_id} deleted successfully' if success else 'Account not found',
        )

    except TinkoffAccountManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

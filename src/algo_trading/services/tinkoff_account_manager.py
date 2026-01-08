"""TinkoffAccountManager Service - Account Lifecycle Management."""

from uuid import UUID

from aiomisc import get_context
from beanie import PydanticObjectId
from t_tech.invest.schemas import MoneyValue

from src.algo_trading.adapters.dto_models.tinkoff_account import (
    CreateTinkoffAccountDTO,
    TinkoffAccountDTO,
    UpdateTinkoffAccountStatusDTO,
)
from src.algo_trading.adapters.models.strategy import TinkoffAccountType
from src.algo_trading.adapters.repositories.tinkoff_account_repository import (
    TinkoffAccountRepository,
)
from src.consts import TINKOFF_INVEST, TINKOFF_INVEST_SANDBOX


class TinkoffAccountManagerError(Exception):
    """TinkoffAccountManager operation failed."""


class TinkoffAccountManager:
    """
    Service for managing Tinkoff brokerage accounts (production and sandbox).

    Handles account creation, synchronization, and lifecycle management.
    Integrates with Tinkoff Invest API for account operations.
    Works with DTOs to maintain separation of concerns.
    """

    def __init__(self) -> None:
        """Initialize TinkoffAccountManager."""
        self._repository = TinkoffAccountRepository

    async def create_sandbox_account(
        self,
        user_id: UUID,
        name: str,
        initial_balance: float = 1000000.0,
        set_as_default: bool = True,
    ) -> TinkoffAccountDTO:
        """
        Create new sandbox account via Tinkoff API.

        Args:
            user_id: User identifier
            name: User-friendly account name
            initial_balance: Initial virtual balance in rubles (default: 1,000,000)
            set_as_default: Set as default sandbox account for user

        Returns:
            Created sandbox account DTO

        Raises:
            TinkoffAccountManagerError: If account creation fails
        """
        try:
            sandbox_client = await get_context()[TINKOFF_INVEST_SANDBOX]
            if not sandbox_client:
                raise TinkoffAccountManagerError('Sandbox client not initialized')
            response = await sandbox_client.sandbox.open_sandbox_account()
            tinkoff_account_id = response.account_id

            await sandbox_client.sandbox.sandbox_pay_in(
                account_id=tinkoff_account_id,
                amount=self._convert_to_money_value(initial_balance),
            )

            accounts_response = await sandbox_client.users.get_accounts()
            account_info = None
            for acc in accounts_response.accounts:
                if acc.id == tinkoff_account_id:
                    account_info = acc
                    break

            if not account_info:
                raise TinkoffAccountManagerError(
                    f'Created sandbox account {tinkoff_account_id} not found in API response',
                )

            create_dto = CreateTinkoffAccountDTO(
                account_id=tinkoff_account_id,
                account_type=TinkoffAccountType.SANDBOX,
                name=name,
                user_id=user_id,
                is_default=set_as_default,
                status=str(account_info.status),
                access_level=str(account_info.access_level),
                initial_balance=initial_balance,
            )

            created_account = await self._repository.create(create_dto)

            if set_as_default:
                await self._repository.set_default_account(
                    user_id=user_id,
                    account_id=created_account.id,
                    account_type=TinkoffAccountType.SANDBOX,
                )

            return created_account

        except Exception as e:
            raise TinkoffAccountManagerError(f'Failed to create sandbox account: {e}') from e

    async def sync_production_accounts(self, user_id: UUID) -> list[TinkoffAccountDTO]:
        """
        Synchronize production accounts from Tinkoff API.

        Fetches user's real trading accounts from Tinkoff API and creates/updates
        them in MongoDB. Useful for onboarding or refreshing account list.

        Args:
            user_id: User identifier

        Returns:
            List of synchronized production account DTOs

        Raises:
            TinkoffAccountManagerError: If synchronization fails
        """
        try:
            prod_client = await get_context()[TINKOFF_INVEST]
            if not prod_client:
                raise TinkoffAccountManagerError('Production client not initialized')

            accounts_response = await prod_client.users.get_accounts()

            synced_accounts = []
            for api_account in accounts_response.accounts:
                existing = await self._repository.get_by_tinkoff_account_id(api_account.id)

                if existing:
                    status_dto = UpdateTinkoffAccountStatusDTO(
                        status=str(api_account.status),
                        access_level=str(api_account.access_level),
                    )
                    updated = await self._repository.update_account_status(
                        account_id=existing.id,
                        status_dto=status_dto,
                    )
                    if updated:
                        synced_accounts.append(updated)
                else:
                    create_dto = CreateTinkoffAccountDTO(
                        account_id=api_account.id,
                        account_type=TinkoffAccountType.PRODUCTION,
                        name=api_account.name or f'Production Account {api_account.id[:8]}',
                        user_id=user_id,
                        is_default=False,  # User must explicitly set default
                        status=str(api_account.status),
                        access_level=str(api_account.access_level),
                    )
                    created = await self._repository.create(create_dto)
                    synced_accounts.append(created)

            return synced_accounts

        except Exception as e:
            raise TinkoffAccountManagerError(f'Failed to sync production accounts: {e}') from e

    async def get_user_accounts(
        self,
        user_id: UUID,
        account_type: TinkoffAccountType | None = None,
    ) -> list[TinkoffAccountDTO]:
        """
        Get all accounts for a user.

        Args:
            user_id: User identifier
            account_type: Optional filter by production/sandbox

        Returns:
            List of user's account DTOs
        """
        return await self._repository.get_user_accounts(user_id, account_type)

    async def get_default_account(
        self,
        user_id: UUID,
        account_type: TinkoffAccountType,
    ) -> TinkoffAccountDTO | None:
        """
        Get user's default account for specified type.

        Args:
            user_id: User identifier
            account_type: Production or sandbox

        Returns:
            Default account DTO or None if not set
        """
        return await self._repository.get_default_account(user_id, account_type)

    async def set_default_account(
        self,
        user_id: UUID,
        account_id: PydanticObjectId,
    ) -> TinkoffAccountDTO:
        """
        Set account as default for user.

        Args:
            user_id: User identifier
            account_id: Account to make default

        Returns:
            Updated account DTO

        Raises:
            TinkoffAccountManagerError: If account not found or doesn't belong to user
        """
        account = await self._repository.get_by_id(account_id)

        if not account:
            raise TinkoffAccountManagerError(f'Account {account_id} not found')

        if account.user_id != user_id:
            raise TinkoffAccountManagerError(
                f'Account {account_id} does not belong to user {user_id}',
            )

        await self._repository.set_default_account(
            user_id=user_id,
            account_id=account_id,
            account_type=account.account_type,
        )

        # Reload account to get updated is_default field
        updated = await self._repository.get_by_id(account_id)
        if not updated:
            raise TinkoffAccountManagerError(f'Failed to reload account {account_id}')

        return updated

    async def delete_account(self, user_id: UUID, account_id: PydanticObjectId) -> bool:
        """
        Delete account.

        Args:
            user_id: User identifier
            account_id: Account to delete

        Returns:
            True if deleted

        Raises:
            TinkoffAccountManagerError: If account not found or doesn't belong to user
        """
        account = await self._repository.get_by_id(account_id)

        if not account:
            raise TinkoffAccountManagerError(f'Account {account_id} not found')

        if account.user_id != user_id:
            raise TinkoffAccountManagerError(
                f'Account {account_id} does not belong to user {user_id}',
            )

        return await self._repository.delete(account_id)

    async def fund_sandbox_account(
        self,
        user_id: UUID,
        account_id: PydanticObjectId,
        amount: float,
    ) -> TinkoffAccountDTO:
        """
        Add funds to sandbox account.

        Args:
            user_id: User identifier
            account_id: Sandbox account ID
            amount: Amount to add in rubles

        Returns:
            Updated account DTO

        Raises:
            TinkoffAccountManagerError: If operation fails or account is not sandbox
        """
        account = await self._repository.get_by_id(account_id)

        if not account:
            raise TinkoffAccountManagerError(f'Account {account_id} not found')

        if account.user_id != user_id:
            raise TinkoffAccountManagerError(
                f'Account {account_id} does not belong to user {user_id}',
            )

        if account.account_type != TinkoffAccountType.SANDBOX:
            raise TinkoffAccountManagerError(
                f'Account {account_id} is not a sandbox account',
            )

        try:
            sandbox_client = await get_context()[TINKOFF_INVEST_SANDBOX]
            if not sandbox_client:
                raise TinkoffAccountManagerError('Sandbox client not initialized')

            await sandbox_client.sandbox.sandbox_pay_in(
                account_id=account.account_id,
                amount=self._convert_to_money_value(amount),
            )

            return account

        except Exception as e:
            raise TinkoffAccountManagerError(f'Failed to fund sandbox account: {e}') from e

    @staticmethod
    def _convert_to_money_value(amount: float) -> MoneyValue:
        """
        Convert float amount to Tinkoff MoneyValue format.

        Args:
            amount: Amount in rubles

        Returns:
            MoneyValue object
        """
        units = int(amount)
        nano = int((amount - units) * 1_000_000_000)

        return MoneyValue(currency='rub', units=units, nano=nano)

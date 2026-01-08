"""TinkoffClient Factory - Routes to production or sandbox client based on account type."""

from beanie import PydanticObjectId

from src.algo_trading.adapters.models.tinkoff_account import TinkoffAccountType
from src.algo_trading.adapters.repositories.tinkoff_account_repository import (
    TinkoffAccountRepository,
)
from src.algo_trading.adapters.tinkoff_client import TinkoffInvestClient
from src.consts import TINKOFF_INVEST, TINKOFF_INVEST_SANDBOX


class TinkoffClientFactoryError(Exception):
    """TinkoffClientFactory operation failed."""


class TinkoffClientFactory:
    """
    Factory for creating TinkoffInvestClient with correct routing.

    Routes to production or sandbox client based on account type.
    Implements Strategy pattern for client selection.
    """

    @staticmethod
    async def create_client_for_account(account_id: PydanticObjectId) -> TinkoffInvestClient:
        """
        Create TinkoffInvestClient for specified account.

        Routes to production or sandbox client based on account type.

        Args:
            account_id: TinkoffAccount MongoDB ID

        Returns:
            TinkoffInvestClient configured for account's environment

        Raises:
            TinkoffClientFactoryError: If account not found or client creation fails
        """
        account_dto = await TinkoffAccountRepository.get_by_id(account_id)

        if not account_dto:
            raise TinkoffClientFactoryError(f'Account {account_id} not found')

        context_name = (
            TINKOFF_INVEST_SANDBOX
            if account_dto.account_type == TinkoffAccountType.SANDBOX
            else TINKOFF_INVEST
        )

        client = TinkoffInvestClient(
            account_id=account_dto.account_id,
            context_name=context_name,
        )

        await client.init_client()

        return client

    @staticmethod
    def create_production_client(account_id: str) -> TinkoffInvestClient:
        """
        Create production TinkoffInvestClient.

        Args:
            account_id: Tinkoff API account identifier

        Returns:
            TinkoffInvestClient for production environment
        """
        return TinkoffInvestClient(
            account_id=account_id,
            context_name=TINKOFF_INVEST,
        )

    @staticmethod
    def create_sandbox_client(account_id: str) -> TinkoffInvestClient:
        """
        Create sandbox TinkoffInvestClient.

        Args:
            account_id: Tinkoff API account identifier

        Returns:
            TinkoffInvestClient for sandbox environment
        """
        return TinkoffInvestClient(
            account_id=account_id,
            context_name=TINKOFF_INVEST_SANDBOX,
        )

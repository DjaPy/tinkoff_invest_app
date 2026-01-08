"""Strategy Repository - Hexagonal Architecture Adapter.

Data access layer for TradingStrategy model.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.algo_trading.adapters.models.strategy import (
    TinkoffAccountDocument,
    TinkoffAccountType,
)
from src.algo_trading.ports.api.v1.schemas.strategies_schema import UpdateStrategyRequestSchema
from src.algo_trading.adapters.models import (
    RiskControls,
    StrategyStatusEnum,
    StrategyTypeEnum,
    TradingStrategyDocument,
)


class InvalidStateTransitionError(Exception):
    """Raised when strategy state transition is invalid."""


class StrategyRepository:
    """
    Repository for TradingStrategy CRUD operations.

    Encapsulates MongoDB access via Beanie ODM.
    """

    @staticmethod
    async def create(strategy: TradingStrategyDocument) -> TradingStrategyDocument:
        """
        Create a new trading strategy.

        Args:
            strategy: TradingStrategy instance to persist

        Returns:
            Saved strategy with generated ID
        """
        await strategy.insert()
        return strategy

    @staticmethod
    async def create_from_request(
        name: str,
        strategy_type: StrategyTypeEnum,
        parameters: dict[str, Any],
        risk_controls: RiskControls,
        created_by: UUID,
        tinkoff_account_type: TinkoffAccountType,
    ) -> TradingStrategyDocument:
        """
        Create a new trading strategy from API request data.

        This method encapsulates the logic of creating a TradingStrategyDocument
        from raw request data, following the Repository pattern.

        Args:
            name: Strategy name
            strategy_type: Type of trading strategy
            parameters: Strategy-specific parameters
            risk_controls: Risk management configuration
            created_by: User ID who created the strategy
            tinkoff_account_type: Tinkoff account type

        Returns:
            Saved strategy with generated ID

        Raises:
            ValueError: If no default account found for account type
        """
        tinkoff_account = await TinkoffAccountDocument.find_one(
            TinkoffAccountDocument.user_id == created_by,
            TinkoffAccountDocument.account_type == tinkoff_account_type,
            TinkoffAccountDocument.is_default == True,  # noqa: E712
        )
        if not tinkoff_account:
            raise ValueError(f'No default {tinkoff_account_type.value} account found for user')

        strategy = TradingStrategyDocument(
            name=name,
            strategy_type=strategy_type,
            parameters=parameters,
            risk_controls=risk_controls,
            created_by=created_by,
            tinkoff_account=tinkoff_account,
        )

        await strategy.insert()
        return strategy

    @staticmethod
    async def find_by_id(strategy_id: UUID) -> TradingStrategyDocument | None:
        """
        Find strategy by UUID.

        Args:
            strategy_id: Strategy UUID

        Returns:
            TradingStrategy or None if not found
        """
        return await TradingStrategyDocument.find_one(TradingStrategyDocument.strategy_id == strategy_id)

    @staticmethod
    async def find_by_ids(strategy_ids: list[UUID]) -> list[TradingStrategyDocument]:
        """
        Find multiple strategies by UUIDs.

        Args:
            strategy_ids: List of strategy UUIDs

        Returns:
            List of found strategies (may be fewer than requested if some not found)
        """
        if not strategy_ids:
            return []

        return await TradingStrategyDocument.find(
            TradingStrategyDocument.strategy_id.in_(strategy_ids),  # type: ignore[attr-defined]
        ).to_list()

    @staticmethod
    async def find_all(
        created_by: UUID | None = None,
        status: StrategyStatusEnum | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TradingStrategyDocument]:
        """
        Find strategies with optional filtering.

        Args:
            created_by: Filter by creator
            status: Filter by status
            limit: Maximum results
            offset: Skip first N results

        Returns:
            List of strategies
        """
        query: dict[str, Any] = {}

        if created_by:
            query['created_by'] = created_by

        if status:
            query['status'] = status

        return await TradingStrategyDocument.find(query).skip(offset).limit(limit).to_list()

    @staticmethod
    async def update(strategy: TradingStrategyDocument) -> TradingStrategyDocument:
        """
        Update existing strategy.

        Args:
            strategy: Strategy with updated fields

        Returns:
            Updated strategy

        Raises:
            ValueError: If strategy not found
        """
        await strategy.save()
        return strategy

    @staticmethod
    async def update_strategy(
        strategy_id: UUID,
        update_data: UpdateStrategyRequestSchema,
    ) -> TradingStrategyDocument | None:
        """
        Update strategy with partial data.

        Args:
            strategy_id: Strategy UUID
            update_data: Fields to update (name, parameters, risk_controls)

        Returns:
            Updated strategy or None if not found
        """
        strategy = await StrategyRepository.find_by_id(strategy_id)
        if not strategy:
            return None

        if update_data.name:
            strategy.name = update_data.name

        if update_data.parameters:
            strategy.parameters = update_data.parameters

        if update_data.risk_controls:
            strategy.risk_controls = update_data.risk_controls

        strategy.updated_at = datetime.now(timezone.utc)

        await strategy.save()
        return strategy

    @staticmethod
    async def delete(strategy_id: UUID) -> bool:
        """
        Delete strategy by ID.

        Args:
            strategy_id: Strategy UUID

        Returns:
            True if deleted, False if not found
        """
        strategy = await StrategyRepository.find_by_id(strategy_id)
        if not strategy:
            return False

        await strategy.delete()
        return True

    @staticmethod
    async def count(created_by: UUID | None = None, status: StrategyStatusEnum | None = None) -> int:
        """
        Count strategies matching filters.

        Args:
            created_by: Filter by creator
            status: Filter by status

        Returns:
            Count of matching strategies
        """
        query: dict[str, Any] = {}

        if created_by:
            query['created_by'] = created_by

        if status:
            query['status'] = status

        return await TradingStrategyDocument.find(query).count()

    @staticmethod
    async def find_active_strategies(created_by: UUID | None = None) -> list[TradingStrategyDocument]:
        """
        Find all active strategies.

        Args:
            created_by: Optional user filter

        Returns:
            List of active strategies
        """
        return await StrategyRepository.find_all(created_by=created_by, status=StrategyStatusEnum.ACTIVE)

    @staticmethod
    async def pause_strategy(strategy_id: UUID) -> TradingStrategyDocument:
        """
        Pause strategy execution.

        Args:
            strategy_id: Strategy UUID

        Returns:
            Updated strategy with PAUSED status

        Raises:
            ValueError: If strategy not found
            InvalidStateTransitionError: If status transition is invalid
        """
        strategy = await StrategyRepository.find_by_id(strategy_id)
        if not strategy:
            raise ValueError(f'Strategy {strategy_id} not found')

        try:
            strategy.update_status(StrategyStatusEnum.PAUSED)
        except ValueError as e:
            raise InvalidStateTransitionError(str(e)) from e

        await strategy.save()
        return strategy

    @staticmethod
    async def start_strategy(strategy_id: UUID) -> TradingStrategyDocument:
        """
        Start strategy execution.

        Args:
            strategy_id: Strategy UUID

        Returns:
            Updated strategy with ACTIVE status

        Raises:
            ValueError: If strategy not found
            InvalidStateTransitionError: If status transition is invalid
        """
        strategy = await StrategyRepository.find_by_id(strategy_id)
        if not strategy:
            raise ValueError(f'Strategy {strategy_id} not found')

        try:
            strategy.update_status(StrategyStatusEnum.ACTIVE)
        except ValueError as e:
            raise InvalidStateTransitionError(str(e)) from e

        await strategy.save()
        return strategy

    @staticmethod
    async def stop_strategy(strategy_id: UUID) -> TradingStrategyDocument:
        """
        Stop strategy execution.

        Args:
            strategy_id: Strategy UUID

        Returns:
            Updated strategy with STOPPED status

        Raises:
            ValueError: If strategy not found
            InvalidStateTransitionError: If status transition is invalid
        """
        strategy = await StrategyRepository.find_by_id(strategy_id)
        if not strategy:
            raise ValueError(f'Strategy {strategy_id} not found')

        try:
            strategy.update_status(StrategyStatusEnum.STOPPED)
        except ValueError as e:
            raise InvalidStateTransitionError(str(e)) from e

        await strategy.save()
        return strategy

    @staticmethod
    async def clone_to_sandbox(
        strategy_id: UUID,
        sandbox_account: TinkoffAccountDocument,
    ) -> TradingStrategyDocument:
        """
        Clone existing strategy to sandbox account.

        Creates a copy of the strategy with same parameters but linked
        to sandbox account for safe testing. Status is reset to INACTIVE.

        Args:
            strategy_id: Source strategy UUID
            sandbox_account: TinkoffAccountDocument

        Returns:
            Cloned strategy with new UUID and sandbox account

        Raises:
            ValueError: If strategy not found
        """
        source_strategy = await StrategyRepository.find_by_id(strategy_id)
        if not source_strategy:
            raise ValueError(f'Strategy {strategy_id} not found')

        cloned_strategy = TradingStrategyDocument(
            name=f'{source_strategy.name} (Sandbox Clone)',
            strategy_type=source_strategy.strategy_type,
            status=StrategyStatusEnum.INACTIVE,
            parameters=source_strategy.parameters,
            risk_controls=source_strategy.risk_controls,
            created_by=source_strategy.created_by,
            tinkoff_account=sandbox_account,
        )

        await cloned_strategy.insert()
        return cloned_strategy

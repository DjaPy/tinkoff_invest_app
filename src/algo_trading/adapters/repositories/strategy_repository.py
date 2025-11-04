"""Strategy Repository - Hexagonal Architecture Adapter.

Data access layer for TradingStrategy model.
"""

from uuid import UUID

from src.algo_trading.adapters.models import StrategyStatusEnum, TradingStrategyDocument


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
        created_by: str | None = None,
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
        query = {}

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
    async def count(created_by: str | None = None, status: StrategyStatusEnum | None = None) -> int:
        """
        Count strategies matching filters.

        Args:
            created_by: Filter by creator
            status: Filter by status

        Returns:
            Count of matching strategies
        """
        query = {}

        if created_by:
            query['created_by'] = created_by

        if status:
            query['status'] = status

        return await TradingStrategyDocument.find(query).count()

    @staticmethod
    async def find_active_strategies(created_by: None | str = None) -> list[TradingStrategyDocument]:
        """
        Find all active strategies.

        Args:
            created_by: Optional user filter

        Returns:
            List of active strategies
        """
        return await StrategyRepository.find_all(created_by=created_by, status=StrategyStatusEnum.ACTIVE)

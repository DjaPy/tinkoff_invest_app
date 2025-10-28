"""Strategy Repository - Hexagonal Architecture Adapter.

Data access layer for TradingStrategy model.
"""

from uuid import UUID

from src.algo_trading.adapters.models import StrategyStatus, TradingStrategy


class StrategyRepository:
    """
    Repository for TradingStrategy CRUD operations.

    Encapsulates MongoDB access via Beanie ODM.
    """

    @staticmethod
    async def create(strategy: TradingStrategy) -> TradingStrategy:
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
    async def find_by_id(strategy_id: UUID) -> TradingStrategy | None:
        """
        Find strategy by UUID.

        Args:
            strategy_id: Strategy UUID

        Returns:
            TradingStrategy or None if not found
        """
        return await TradingStrategy.find_one(TradingStrategy.strategy_id == strategy_id)

    @staticmethod
    async def find_all(
        created_by: str | None = None,
        status: StrategyStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TradingStrategy]:
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

        return await TradingStrategy.find(query).skip(offset).limit(limit).to_list()

    @staticmethod
    async def update(strategy: TradingStrategy) -> TradingStrategy:
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
    async def count(created_by: str | None = None, status: StrategyStatus | None = None) -> int:
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

        return await TradingStrategy.find(query).count()

    @staticmethod
    async def find_active_strategies(created_by: None | str = None) -> list[TradingStrategy]:
        """
        Find all active strategies.

        Args:
            created_by: Optional user filter

        Returns:
            List of active strategies
        """
        return await StrategyRepository.find_all(created_by=created_by, status=StrategyStatus.ACTIVE)

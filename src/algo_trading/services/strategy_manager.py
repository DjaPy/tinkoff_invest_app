"""StrategyManager Service - Application Use Case Layer.

Orchestrates strategy lifecycle: create, start, pause, stop, delete.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.algo_trading.adapters.models import (StrategyStatus, TradingSession,
                                              TradingStrategy)
from src.algo_trading.adapters.repositories.strategy_repository import \
    StrategyRepository
from src.algo_trading.domain.risk.risk_evaluator import RiskLimits


class StrategyManagerError(Exception):
    """Strategy management operation failed."""

    pass


class StrategyManager:
    """
    Application service for strategy lifecycle management.

    Orchestrates domain logic, repository access, and business rules.
    """

    def __init__(self, strategy_repo: StrategyRepository):
        """
        Initialize StrategyManager.

        Args:
            strategy_repo: Repository for strategy persistence
        """
        self.strategy_repo = strategy_repo

    async def create_strategy(
        self,
        name: str,
        strategy_type: str,
        parameters: dict,
        risk_controls: dict,
        created_by: str,
    ) -> TradingStrategy:
        """
        Create a new trading strategy.

        Args:
            name: Strategy name
            strategy_type: Strategy type (momentum, mean_reversion, etc.)
            parameters: Strategy-specific parameters
            risk_controls: Risk management configuration
            created_by: User identifier

        Returns:
            Created TradingStrategy

        Raises:
            StrategyManagerError: If validation fails
        """
        # Validate uniqueness (name per user)
        existing = await self.strategy_repo.find_all(created_by=created_by)
        if any(s.name == name for s in existing):
            raise StrategyManagerError(f"Strategy '{name}' already exists for user {created_by}")

        # Create strategy model
        from ..adapters.models.strategy import RiskControls

        risk_controls_model = RiskControls(**risk_controls)

        strategy = TradingStrategy(
            name=name,
            strategy_type=strategy_type,
            parameters=parameters,
            risk_controls=risk_controls_model,
            created_by=created_by,
        )

        # Persist
        await self.strategy_repo.create(strategy)

        return strategy

    async def get_strategy(self, strategy_id: UUID) -> TradingStrategy:
        """
        Get strategy by ID.

        Args:
            strategy_id: Strategy UUID

        Returns:
            TradingStrategy

        Raises:
            StrategyManagerError: If not found
        """
        strategy = await self.strategy_repo.find_by_id(strategy_id)
        if not strategy:
            raise StrategyManagerError(f"Strategy {strategy_id} not found")

        return strategy

    async def list_strategies(
        self,
        created_by: str | None = None,
        status: StrategyStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[TradingStrategy], int]:
        """
        List strategies with filtering and pagination.

        Args:
            created_by: Filter by creator
            status: Filter by status
            limit: Max results
            offset: Skip N results

        Returns:
            Tuple of (strategies, total_count)
        """
        strategies = await self.strategy_repo.find_all(
            created_by=created_by,
            status=status,
            limit=limit,
            offset=offset,
        )

        total = await self.strategy_repo.count(created_by=created_by, status=status)

        return strategies, total

    async def update_strategy(
        self,
        strategy_id: UUID,
        parameters: dict[str, Any] | None = None,
        risk_controls: dict[str, Any] | None = None,
    ) -> TradingStrategy:
        """
        Update strategy configuration.

        Args:
            strategy_id: Strategy UUID
            parameters: Updated strategy parameters
            risk_controls: Updated risk controls

        Returns:
            Updated strategy

        Raises:
            StrategyManagerError: If update fails or strategy is active
        """
        strategy = await self.get_strategy(strategy_id)

        # Cannot update active strategy
        if strategy.status == StrategyStatus.ACTIVE:
            raise StrategyManagerError("Cannot update active strategy. Pause or stop it first.")

        if parameters is not None:
            strategy.parameters = parameters

        if risk_controls is not None:
            from ..adapters.models.strategy import RiskControls

            strategy.risk_controls = RiskControls(**risk_controls)

        strategy.updated_at = datetime.utcnow()

        await self.strategy_repo.update(strategy)

        return strategy

    async def start_strategy(
        self,
        strategy_id: UUID,
        starting_capital: Decimal,
    ) -> tuple[TradingStrategy, TradingSession]:
        """
        Start strategy execution (activate trading).

        Args:
            strategy_id: Strategy UUID
            starting_capital: Initial capital for session

        Returns:
            Tuple of (updated_strategy, trading_session)

        Raises:
            StrategyManagerError: If cannot start
        """
        strategy = await self.get_strategy(strategy_id)

        # Validate status transition
        if not strategy.can_transition_to(StrategyStatus.ACTIVE):
            raise StrategyManagerError(
                f"Cannot start strategy in {strategy.status} status. "
                f"Must be INACTIVE or PAUSED."
            )

        # Create trading session
        session = TradingSession(
            strategy_id=strategy.strategy_id,
            starting_capital=starting_capital,
        )
        await session.insert()

        # Update strategy status
        strategy.update_status(StrategyStatus.ACTIVE)
        await self.strategy_repo.update(strategy)

        return strategy, session

    async def pause_strategy(self, strategy_id: UUID) -> TradingStrategy:
        """
        Pause strategy execution (keep positions, stop new orders).

        Args:
            strategy_id: Strategy UUID

        Returns:
            Updated strategy

        Raises:
            StrategyManagerError: If cannot pause
        """
        strategy = await self.get_strategy(strategy_id)

        if not strategy.can_transition_to(StrategyStatus.PAUSED):
            raise StrategyManagerError(
                f"Cannot pause strategy in {strategy.status} status. Must be ACTIVE."
            )

        strategy.update_status(StrategyStatus.PAUSED)
        await self.strategy_repo.update(strategy)

        return strategy

    async def stop_strategy(
        self,
        strategy_id: UUID,
        ending_capital: Decimal,
    ) -> tuple[TradingStrategy, TradingSession]:
        """
        Stop strategy execution (close positions, end session).

        Args:
            strategy_id: Strategy UUID
            ending_capital: Final capital for session

        Returns:
            Tuple of (updated_strategy, ended_session)

        Raises:
            StrategyManagerError: If cannot stop
        """
        strategy = await self.get_strategy(strategy_id)

        if not strategy.can_transition_to(StrategyStatus.STOPPED):
            raise StrategyManagerError(
                f"Cannot stop strategy in {strategy.status} status. "
                f"Must be ACTIVE or PAUSED."
            )

        # Find active session
        active_session = await TradingSession.find_one(
            TradingSession.strategy_id == strategy.strategy_id,
            TradingSession.session_end == None,  # noqa: E711
        )

        if not active_session:
            raise StrategyManagerError(f"No active session found for strategy {strategy_id}")

        # End session
        active_session.end_session(ending_capital)
        await active_session.save()

        # Update strategy status
        strategy.update_status(StrategyStatus.STOPPED)
        await self.strategy_repo.update(strategy)

        return strategy, active_session

    async def delete_strategy(self, strategy_id: UUID) -> bool:
        """
        Delete strategy.

        Args:
            strategy_id: Strategy UUID

        Returns:
            True if deleted

        Raises:
            StrategyManagerError: If strategy is active
        """
        strategy = await self.get_strategy(strategy_id)

        # Cannot delete active strategy
        if strategy.status == StrategyStatus.ACTIVE:
            raise StrategyManagerError("Cannot delete active strategy. Stop it first.")

        return await self.strategy_repo.delete(strategy_id)

    def convert_to_risk_limits(self, strategy: TradingStrategy) -> RiskLimits:
        """
        Convert strategy risk controls to domain RiskLimits.

        Args:
            strategy: TradingStrategy with risk_controls

        Returns:
            RiskLimits domain object
        """
        rc = strategy.risk_controls

        return RiskLimits(
            max_position_size=rc.max_position_size,
            max_portfolio_value=rc.max_portfolio_value,
            stop_loss_percent=rc.stop_loss_percent,
            max_drawdown_percent=rc.max_drawdown_percent,
            daily_loss_limit=rc.daily_loss_limit,
            max_orders_per_day=rc.max_orders_per_day,
        )

"""Trading Session Manager - Application Service Layer.

Manages trading sessions lifecycle and session-level risk tracking.
"""

from decimal import Decimal
from uuid import UUID

from src.algo_trading.adapters.models import TradingSessionDocument


class SessionManagerError(Exception):
    """Session management operation failed."""


class SessionManager:
    """
    Service for managing trading sessions.

    Handles session creation, updates, and queries.
    """

    async def get_active_session(self, strategy_id: UUID) -> TradingSessionDocument | None:
        """
        Get active session for strategy.

        Args:
            strategy_id: Strategy UUID

        Returns:
            Active TradingSession or None
        """
        return await TradingSessionDocument.find_one(
            TradingSessionDocument.strategy_id == strategy_id,
            TradingSessionDocument.session_end == None,  # noqa: E711
        )

    async def get_session_by_id(self, session_id: UUID) -> TradingSessionDocument | None:
        """
        Get session by ID.

        Args:
            session_id: Session UUID

        Returns:
            TradingSession or None
        """
        return await TradingSessionDocument.get(session_id)

    async def get_strategy_sessions(
        self,
        strategy_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TradingSessionDocument]:
        """
        Get all sessions for strategy.

        Args:
            strategy_id: Strategy UUID
            limit: Max results
            offset: Skip N results

        Returns:
            List of trading sessions
        """
        return (
            await TradingSessionDocument.find(TradingSessionDocument.strategy_id == strategy_id)
            .sort('-session_start')
            .skip(offset)
            .limit(limit)
            .to_list()
        )

    async def update_session_metrics(
        self,
        session_id: UUID,
        orders_placed: int | None = None,
        orders_filled: int | None = None,
        orders_cancelled: int | None = None,
        orders_rejected: int | None = None,
        total_pnl: Decimal | None = None,
        max_drawdown: Decimal | None = None,
    ) -> TradingSessionDocument:
        """
        Update session metrics.

        Args:
            session_id: Session UUID
            orders_placed: Total orders placed
            orders_filled: Total filled orders
            orders_cancelled: Total cancelled orders
            orders_rejected: Total rejected orders
            total_pnl: Total P&L for session
            max_drawdown: Maximum drawdown reached

        Returns:
            Updated session

        Raises:
            SessionManagerError: If session not found
        """
        session = await TradingSessionDocument.get(session_id)
        if not session:
            raise SessionManagerError(f'Session {session_id} not found')

        # Update metrics
        if orders_placed is not None:
            session.orders_placed = orders_placed
        if orders_filled is not None:
            session.orders_filled = orders_filled
        if orders_cancelled is not None:
            session.orders_cancelled = orders_cancelled
        if orders_rejected is not None:
            session.orders_rejected = orders_rejected
        if total_pnl is not None:
            session.total_pnl = total_pnl
        if max_drawdown is not None:
            session.update_drawdown(max_drawdown)

        await session.save()
        return session

    async def record_trade(
        self,
        session_id: UUID,
        pnl: Decimal,
    ) -> TradingSessionDocument:
        """
        Record a trade in session.

        Args:
            session_id: Session UUID
            pnl: Profit/loss for the trade

        Returns:
            Updated session

        Raises:
            SessionManagerError: If session not found or ended
        """
        session = await TradingSessionDocument.get(session_id)
        if not session:
            raise SessionManagerError(f'Session {session_id} not found')

        if session.session_end is not None:
            raise SessionManagerError(f'Session {session_id} has already ended')

        # Update session totals
        session.total_pnl = (session.total_pnl or Decimal('0')) + pnl
        session.orders_filled = (session.orders_filled or 0) + 1

        await session.save()
        return session

    async def record_risk_violation(self, session_id: UUID) -> TradingSessionDocument:
        """
        Record a risk violation in session.

        Args:
            session_id: Session UUID

        Returns:
            Updated session

        Raises:
            SessionManagerError: If session not found
        """
        session = await TradingSessionDocument.get(session_id)
        if not session:
            raise SessionManagerError(f'Session {session_id} not found')

        session.record_risk_violation()
        await session.save()
        return session

    async def calculate_session_return(self, session_id: UUID) -> Decimal:
        """
        Calculate session return percentage.

        Args:
            session_id: Session UUID

        Returns:
            Return percentage

        Raises:
            SessionManagerError: If session not found
        """
        session = await TradingSessionDocument.get(session_id)
        if not session:
            raise SessionManagerError(f'Session {session_id} not found')

        if session.starting_capital == 0:
            return Decimal('0')

        total_pnl = session.total_pnl or Decimal('0')
        return (total_pnl / session.starting_capital) * Decimal('100')

    async def calculate_session_sharpe_ratio(
        self,
        session_id: UUID,
        risk_free_rate: Decimal = Decimal('0.02'),
    ) -> Decimal:
        """
        Calculate session Sharpe ratio (simplified).

        Args:
            session_id: Session UUID
            risk_free_rate: Annual risk-free rate (default 2%)

        Returns:
            Sharpe ratio estimate

        Raises:
            SessionManagerError: If session not found

        Note:
            This is a simplified calculation. For accurate Sharpe ratio,
            use PerformanceAnalytics service with trade history.
        """
        session = await TradingSessionDocument.get(session_id)
        if not session:
            raise SessionManagerError(f'Session {session_id} not found')

        if not session.max_drawdown_reached or session.max_drawdown_reached == 0:
            return Decimal('0')

        return_pct = await self.calculate_session_return(session_id)
        risk_pct = abs(session.max_drawdown_reached) * Decimal('100')

        if risk_pct == 0:
            return Decimal('0')

        # Simple risk-adjusted return
        return (return_pct - risk_free_rate) / risk_pct

    async def get_session_statistics(self, session_id: UUID) -> dict:
        """
        Get comprehensive session statistics.

        Args:
            session_id: Session UUID

        Returns:
            Dictionary of session statistics

        Raises:
            SessionManagerError: If session not found
        """
        session = await TradingSessionDocument.get(session_id)
        if not session:
            raise SessionManagerError(f'Session {session_id} not found')

        duration = None
        if session.session_end:
            duration = (session.session_end - session.session_start).total_seconds()

        return {
            'session_id': str(session.session_id),
            'strategy_id': str(session.strategy_id),
            'session_start': session.session_start,
            'session_end': session.session_end,
            'duration_seconds': duration,
            'starting_capital': session.starting_capital,
            'ending_capital': session.ending_capital,
            'total_pnl': session.total_pnl,
            'return_pct': await self.calculate_session_return(session_id),
            'orders_placed': session.orders_placed,
            'orders_filled': session.orders_filled,
            'orders_cancelled': session.orders_cancelled,
            'orders_rejected': session.orders_rejected,
            'fill_rate': (
                (session.orders_filled / session.orders_placed * 100)
                if session.orders_placed and session.orders_placed > 0
                else Decimal('0')
            ),
            'max_drawdown_reached': session.max_drawdown_reached,
            'risk_violations': session.risk_violations,
            'is_active': session.session_end is None,
        }

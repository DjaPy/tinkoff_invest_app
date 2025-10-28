"""TradingSession Beanie model - Hexagonal Architecture Adapter."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field, ValidationInfo, field_validator


class TradingSession(Document):
    """
    Time-bounded strategy execution period.

    Tracks session lifecycle, P&L, and provides session-level statistics.
    Follows Hexagonal Architecture as an Adapter (infrastructure layer).
    """

    session_id: UUID = Field(default_factory=uuid4, description='Unique session identifier')
    strategy_id: UUID = Field(description='Strategy being executed')

    session_start: datetime = Field(default_factory=datetime.utcnow, description='Session start')
    session_end: datetime | None = Field(None, description='Session end (None if active)')

    # Session statistics
    orders_placed: int = Field(default=0, ge=0, description='Total orders placed in session')
    orders_filled: int = Field(default=0, ge=0, description='Orders successfully filled')
    orders_cancelled: int = Field(default=0, ge=0, description='Orders cancelled')
    orders_rejected: int = Field(default=0, ge=0, description='Orders rejected')

    # Financial metrics
    total_commission: Decimal = Field(default=Decimal('0'), ge=0, description='Total commissions paid')
    realized_pnl: Decimal = Field(default=Decimal('0'), description='Realized profit/loss')
    starting_capital: Decimal = Field(gt=0, description='Starting capital for session')
    ending_capital: Decimal | None = Field(None, description='Ending capital (None if active)')

    # Risk tracking
    max_drawdown_reached: Decimal = Field(default=Decimal('0'), description='Maximum drawdown during session')
    risk_violations: int = Field(default=0, ge=0, description='Number of risk violations')

    @field_validator('session_end', mode='after')
    @classmethod
    def validate_session_end(cls, v: datetime | None, info: ValidationInfo) -> datetime | None:
        """Session end must be after session start."""
        if v is None:
            return v

        session_start = info.data.get('session_start')
        if session_start and v <= session_start:
            raise ValueError('session_end must be after session_start')
        return v

    @field_validator('orders_filled', 'orders_cancelled', 'orders_rejected', mode='after')
    @classmethod
    def validate_order_counts(cls, v: int, info: ValidationInfo) -> int:
        """Filled + cancelled + rejected cannot exceed total placed."""
        orders_placed = info.data.get('orders_placed', 0)

        # Get all order counts
        orders_filled = info.data.get('orders_filled', 0)
        orders_cancelled = info.data.get('orders_cancelled', 0)
        orders_rejected = info.data.get('orders_rejected', 0)

        total_processed = orders_filled + orders_cancelled + orders_rejected
        if total_processed > orders_placed:
            raise ValueError(f'Processed orders ({total_processed}) exceeds placed orders ({orders_placed})')

        return v

    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.session_end is None

    def end_session(self, ending_capital: Decimal) -> None:
        """
        End the trading session.

        Args:
            ending_capital: Final capital after session

        Raises:
            ValueError: If session already ended or capital is invalid
        """
        if self.session_end is not None:
            raise ValueError('Session already ended')

        if ending_capital <= 0:
            raise ValueError('Ending capital must be positive')

        self.session_end = datetime.utcnow()
        self.ending_capital = ending_capital
        self.realized_pnl = ending_capital - self.starting_capital

    def record_order(self, status: str) -> None:
        """
        Record order execution outcome.

        Args:
            status: Order status ('filled', 'cancelled', 'rejected')
        """
        self.orders_placed += 1

        if status == 'filled':
            self.orders_filled += 1
        elif status == 'cancelled':
            self.orders_cancelled += 1
        elif status == 'rejected':
            self.orders_rejected += 1

    def add_commission(self, commission: Decimal) -> None:
        """Add commission cost to session total."""
        if commission < 0:
            raise ValueError('Commission cannot be negative')

        self.total_commission += commission

    def update_drawdown(self, current_drawdown: Decimal) -> None:
        """Update maximum drawdown if exceeded."""
        self.max_drawdown_reached = min(self.max_drawdown_reached, current_drawdown)

    def record_risk_violation(self) -> None:
        """Increment risk violation counter."""
        self.risk_violations += 1

    class Settings:
        name = 'trading_sessions'
        indexes = [
            'session_id',
            [('strategy_id', 1), ('session_start', -1)],  # Latest sessions first
            'session_end',  # Filter active sessions (NULL)
        ]

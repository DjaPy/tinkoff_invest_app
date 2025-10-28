"""TradeOrder Beanie model - Hexagonal Architecture Adapter."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from beanie import Document
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo


class OrderType(str, Enum):
    """Order type enumeration."""

    MARKET = 'market'
    LIMIT = 'limit'
    STOP_LOSS = 'stop_loss'
    TAKE_PROFIT = 'take_profit'


class OrderSide(str, Enum):
    """Order side enumeration."""

    BUY = 'buy'
    SELL = 'sell'


class OrderStatus(str, Enum):
    """Order execution status."""

    PENDING = 'pending'
    SUBMITTED = 'submitted'
    FILLED = 'filled'
    PARTIALLY_FILLED = 'partially_filled'
    CANCELLED = 'cancelled'
    REJECTED = 'rejected'


class TradeOrder(Document):
    """
    Individual buy/sell order with execution details.

    Immutable after submission - modifications create new orders.
    Follows Hexagonal Architecture as an Adapter (infrastructure layer).
    """

    order_id: UUID = Field(default_factory=uuid4, description='Unique order identifier')
    strategy_id: UUID = Field(description='Originating strategy')
    session_id: UUID = Field(description='Trading session')
    correlation_id: UUID = Field(default_factory=uuid4, description='Audit trail correlation ID')

    instrument: str = Field(min_length=1, description='Trading instrument (ticker/FIGI)')
    order_type: OrderType = Field(description='Order type')
    side: OrderSide = Field(description='Buy or sell')

    quantity: Decimal = Field(gt=0, description='Order quantity (shares/lots)')
    price: Decimal = Field(default=Decimal('0'), gt=0, description='Limit price (None for market)')
    status: OrderStatus = Field(default=OrderStatus.PENDING, description='Current order status')

    submitted_at: datetime = Field(default_factory=datetime.utcnow, description='Submission timestamp')
    filled_at: datetime | None = Field(None, description='Execution timestamp')
    filled_price: Decimal = Field(default=Decimal('0'), gt=0, description='Actual execution price')
    filled_quantity: Decimal = Field(default=Decimal('0'), ge=0, description='Filled quantity')
    commission: Decimal = Field(default=Decimal('0'), ge=0, description='Trading commission')
    external_order_id: str | None = Field(None, description="Broker's order ID")

    _immutable: bool = False

    @field_validator('price', mode='after')
    @classmethod
    def validate_limit_price(cls, v: Decimal | None, info: ValidationInfo) -> Decimal | None:
        """Limit orders must have a price."""
        order_type = info.data.get('order_type')
        if order_type in {OrderType.LIMIT, OrderType.STOP_LOSS, OrderType.TAKE_PROFIT} and v is None:
            raise ValueError(f'{order_type} orders require a price')
        return v

    @field_validator('filled_quantity', mode='after')
    @classmethod
    def validate_filled_quantity(cls, v: Decimal, values: ValidationInfo) -> Decimal:
        """Filled quantity cannot exceed ordered quantity."""
        quantity = values.data.get('quantity', Decimal('0'))
        if v > quantity:
            raise ValueError(f'Filled quantity {v} exceeds ordered quantity {quantity}')
        return v

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        """
        Check if status transition is valid.

        Valid transitions:
        - PENDING → SUBMITTED
        - SUBMITTED → FILLED, PARTIALLY_FILLED, CANCELLED, REJECTED
        - PARTIALLY_FILLED → FILLED, CANCELLED
        """
        valid_transitions = {
            OrderStatus.PENDING: {OrderStatus.SUBMITTED},
            OrderStatus.SUBMITTED: {
                OrderStatus.FILLED,
                OrderStatus.PARTIALLY_FILLED,
                OrderStatus.CANCELLED,
                OrderStatus.REJECTED,
            },
            OrderStatus.PARTIALLY_FILLED: {OrderStatus.FILLED, OrderStatus.CANCELLED},
        }

        return new_status in valid_transitions.get(self.status, set())

    def update_status(
        self,
        new_status: OrderStatus,
        filled_price: Decimal | None = None,
        filled_quantity: Decimal | None = None,
        external_order_id: str | None = None,
    ) -> None:
        """
        Update order status with execution details.

        Raises ValueError if transition invalid or order is immutable.
        """
        if self._immutable:
            raise ValueError('Order is immutable after final status')

        if not self.can_transition_to(new_status):
            raise ValueError(f'Invalid status transition from {self.status} to {new_status}')

        self.status = new_status

        if filled_price is not None:
            self.filled_price = filled_price

        if filled_quantity is not None:
            if filled_quantity > self.quantity:
                raise ValueError(f'Filled quantity {filled_quantity} exceeds order quantity {self.quantity}')
            self.filled_quantity = filled_quantity

        if external_order_id is not None:
            self.external_order_id = external_order_id

        # Mark as filled
        if new_status in {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED}:
            self.filled_at = datetime.utcnow()
            self._immutable = True  # Immutable after final status

    def calculate_total_value(self) -> Decimal:
        """Calculate total order value including commission."""
        if self.filled_price is None:
            return Decimal('0')

        base_value = self.filled_price * self.filled_quantity
        return base_value + self.commission

    class Settings:
        name = 'trade_orders'
        indexes = [
            'order_id',
            'correlation_id',
            [('strategy_id', 1), ('submitted_at', -1)],  # Orders by strategy
            [('session_id', 1), ('submitted_at', -1)],  # Orders by session
            'status',
            'external_order_id',
        ]

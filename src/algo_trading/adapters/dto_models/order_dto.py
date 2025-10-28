from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.algo_trading.adapters.models import OrderSide, OrderType


@dataclass(frozen=True)
class OrderDTO:
    strategy_id: UUID
    session_id: UUID
    instrument: str
    side: OrderSide
    quantity: Decimal
    order_type: OrderType
    limit_price: Decimal = Decimal('0')
    correlation_id: str | None = None

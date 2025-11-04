from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.algo_trading.adapters.models import OrderSideEnum, OrderTypeEnum


@dataclass(frozen=True)
class OrderDTO:
    strategy_id: UUID
    session_id: UUID
    instrument: str
    side: OrderSideEnum
    quantity: Decimal
    order_type: OrderTypeEnum
    limit_price: Decimal = Decimal('0')
    correlation_id: str | None = None

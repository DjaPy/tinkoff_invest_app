from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.algo_trading.enums import OrderSideEnum, OrderStatusEnum, OrderTypeEnum


class TradeAnalytics(BaseModel):
    """Trade analytics response schema."""

    strategy_id: UUID = Field(description='Strategy identifier')
    total_trades: int = Field(ge=0, description='Total number of trades')
    winning_trades: int = Field(ge=0, description='Number of winning trades')
    losing_trades: int = Field(ge=0, description='Number of losing trades')
    win_rate: Decimal = Field(ge=0, le=1, description='Win rate percentage')
    average_profit: Decimal = Field(description='Average profit per trade')
    average_loss: Decimal = Field(description='Average loss per trade')
    profit_factor: Decimal = Field(ge=0, description='Profit factor ratio')




class OrderResponseSchema(BaseModel):
    order_id: UUID = Field(default_factory=uuid4, description='Unique order identifier')
    strategy_id: UUID = Field(description='Originating strategy')
    session_id: UUID = Field(description='Trading session')
    correlation_id: UUID = Field(default_factory=uuid4, description='Audit trail correlation ID')

    instrument: str = Field(min_length=1, description='Trading instrument (ticker/FIGI)')
    order_type: OrderTypeEnum = Field(description='Order type')
    side: OrderSideEnum = Field(description='Buy or sell')

    quantity: Decimal = Field(gt=0, description='Order quantity (shares/lots)')
    price: Decimal = Field(default=Decimal('0'), gt=0, description='Limit price (None for market)')
    status: OrderStatusEnum = Field(default=OrderStatusEnum.PENDING, description='Current order status')

    submitted_at: datetime = Field(default_factory=datetime.now, description='Submission timestamp')
    filled_at: datetime | None = Field(None, description='Execution timestamp')
    filled_price: Decimal = Field(default=Decimal('0'), gt=0, description='Actual execution price')
    filled_quantity: Decimal = Field(default=Decimal('0'), ge=0, description='Filled quantity')
    commission: Decimal = Field(default=Decimal('0'), ge=0, description='Trading commission')
    external_order_id: str | None = Field(None, description="Broker's order ID")


class OrderListResponseSchema(BaseModel):
    """Response schema for listing orders."""

    orders: list[OrderResponseSchema] = Field(description='List of trade orders')
    total: int = Field(ge=0, description='Total number of orders matching filters')
    limit: int = Field(ge=1, le=100, description='Request limit parameter')
    offset: int = Field(ge=0, description='Request offset parameter')


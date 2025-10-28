from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


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

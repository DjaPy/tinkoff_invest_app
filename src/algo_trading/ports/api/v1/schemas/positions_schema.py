from decimal import Decimal

from pydantic import BaseModel, Field

from src.algo_trading.adapters.models import PortfolioPositionDocument


class PositionListResponseSchema(BaseModel):
    """Response schema for listing positions."""

    positions: list[PortfolioPositionDocument] = Field(description='List of portfolio positions')
    total_value: Decimal = Field(ge=0, description='Total portfolio market value')
    total_pnl: Decimal = Field(description='Total unrealized P&L')

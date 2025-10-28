"""
Positions API endpoints - Hexagonal Architecture Inbound Port.

REST API endpoints for managing portfolio positions.
Following FastAPI patterns and RFC7807 error handling.
"""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.algo_trading.adapters.models.position import PortfolioPosition
from src.algo_trading.ports.api.v1.schemas.positions_schema import PositionListResponseSchema

positions_router = APIRouter(prefix='/api/v1/positions', tags=['Portfolio'])


@positions_router.get(
    '/',
    response_model=PositionListResponseSchema,
    summary='List portfolio positions',
    description='Retrieve current portfolio positions across all strategies',
)
async def list_positions(
    strategy_id: UUID | None = Query(None, description='Filter positions by strategy ID'),
    instrument: str | None = Query(None, description='Filter positions by instrument'),
) -> PositionListResponseSchema:
    """
    List portfolio positions with optional filtering (T052).

    Args:
        strategy_id: Optional filter by strategy
        instrument: Optional filter by trading instrument

    Returns:
        List of positions with total portfolio value and P&L

    Raises:
        HTTPException 500: Internal server error
    """
    # Build query filters
    query_filters = []

    if strategy_id:
        query_filters.append(PortfolioPosition.strategy_id == strategy_id)

    if instrument:
        query_filters.append(PortfolioPosition.instrument == instrument)

    # Fetch positions from database
    if query_filters:
        # Combine filters with AND logic
        positions = await PortfolioPosition.find(*query_filters).to_list()
    else:
        positions = await PortfolioPosition.find_all().to_list()

    # Calculate totals
    if len(positions) == 0:
        return PositionListResponse(positions=[], total_value=Decimal('0'), total_pnl=Decimal('0'))
    total_value = sum(pos.market_value for pos in positions)
    total_pnl = sum(pos.unrealized_pnl for pos in positions)

    return PositionListResponseSchema(positions=positions, total_value=total_value, total_pnl=total_pnl)


@positions_router.get(
    '/{position_id}',
    response_model=PortfolioPosition,
    summary='Get position details',
    description='Retrieve detailed information about a specific portfolio position',
)
async def get_position(position_id: UUID) -> PortfolioPosition:
    """
    Get position by ID (T053).

    Args:
        position_id: Unique position identifier

    Returns:
        Position details with computed P&L fields

    Raises:
        HTTPException 404: Position not found
        HTTPException 500: Internal server error
    """
    position = await PortfolioPosition.find_one(PortfolioPosition.position_id == position_id)

    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Position {position_id} not found')

    return position

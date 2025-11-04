"""
Strategies API endpoints - Hexagonal Architecture Inbound Port.

REST API endpoints for managing trading strategies.
Following FastAPI patterns and RFC7807 error handling.
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.algo_trading.enums import StrategyStatusEnum
from src.algo_trading.adapters.models.strategy import TradingStrategyDocument
from src.algo_trading.ports.api.v1.schemas.strategies_schema import (
    CreateStrategyRequestSchema,
    StrategyListResponseSchema,
    UpdateStrategyRequestSchema,
)

strategies_router = APIRouter(prefix='/api/v1/strategies', tags=['Trading Strategies'])


@strategies_router.post(
    '/',
    response_model=TradingStrategyDocument,
    status_code=status.HTTP_201_CREATED,
    summary='Create new trading strategy',
    description='Create a new algorithmic trading strategy with configuration and risk controls',
)
async def create_strategy(request: CreateStrategyRequestSchema) -> TradingStrategyDocument:
    """
    Create a new trading strategy (T042).

    Args:
        request: Strategy creation request with parameters and risk controls

    Returns:
        Created strategy with unique ID and inactive status

    Raises:
        HTTPException 422: Validation error in request data
        HTTPException 500: Internal server error
    """
    # TODO: Implement strategy creation logic using StrategyManager service
    # For now, create a strategy directly (will be replaced with service call)

    strategy = TradingStrategyDocument(
        name=request.name,
        strategy_type=request.strategy_type,
        parameters=request.parameters,
        risk_controls=request.risk_controls,
        created_by='test-user',  # TODO: Get from auth token
    )

    # TODO: Save to database via repository
    await strategy.insert()

    return strategy


@strategies_router.get(
    '/',
    response_model=StrategyListResponseSchema,
    summary='List all trading strategies',
    description='Retrieve all trading strategies for the authenticated user',
)
async def list_strategies() -> StrategyListResponseSchema:
    """
    List all trading strategies (T043).

    Returns:
        List of strategies with total count

    Raises:
        HTTPException 500: Internal server error
    """
    # TODO: Implement filtering by user from auth token
    # TODO: Use repository to fetch strategies

    strategies = await TradingStrategyDocument.find_all().to_list()

    return StrategyListResponseSchema(strategies=strategies, total=len(strategies))


@strategies_router.get(
    '/{strategy_id}',
    response_model=TradingStrategyDocument,
    summary='Get strategy details',
    description='Retrieve detailed information about a specific trading strategy',
)
async def get_strategy(strategy_id: UUID) -> TradingStrategyDocument:
    """
    Get strategy by ID (implied in T043).

    Args:
        strategy_id: Unique strategy identifier

    Returns:
        Strategy details

    Raises:
        HTTPException 404: Strategy not found
        HTTPException 500: Internal server error
    """
    strategy = await TradingStrategyDocument.find_one(TradingStrategyDocument.strategy_id == strategy_id)

    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Strategy {strategy_id} not found')

    return strategy


@strategies_router.put(
    '/{strategy_id}',
    response_model=TradingStrategyDocument,
    summary='Update trading strategy',
    description='Update strategy configuration and risk controls',
)
async def update_strategy(strategy_id: UUID, body: UpdateStrategyRequestSchema) -> TradingStrategyDocument:
    """
    Update existing strategy (T044).

    Args:
        strategy_id: Unique strategy identifier
        body: Strategy update request with optional fields

    Returns:
        Updated strategy

    Raises:
        HTTPException 404: Strategy not found
        HTTPException 422: Validation error in request data
        HTTPException 500: Internal server error
    """
    strategy = await TradingStrategyDocument.find_one(TradingStrategyDocument.strategy_id == strategy_id)

    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Strategy {strategy_id} not found')

    # Update fields if provided
    if body.name is not None:
        strategy.name = body.name

    if body.parameters is not None:
        strategy.parameters = body.parameters

    if body.risk_controls is not None:
        strategy.risk_controls = body.risk_controls

    strategy.updated_at = datetime.now(UTC)

    # TODO: Save via repository
    await strategy.save()

    return strategy


@strategies_router.delete(
    '/{strategy_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Delete trading strategy',
    description='Delete a trading strategy and all associated data',
)
async def delete_strategy(strategy_id: UUID) -> None:
    """
    Delete strategy (T045).

    Args:
        strategy_id: Unique strategy identifier

    Raises:
        HTTPException 404: Strategy not found
        HTTPException 409: Cannot delete active strategy
        HTTPException 500: Internal server error
    """
    strategy = await TradingStrategyDocument.find_one(TradingStrategyDocument.strategy_id == strategy_id)

    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Strategy {strategy_id} not found')

    # Cannot delete active strategy
    if strategy.status == StrategyStatusEnum.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Cannot delete active strategy. Stop the strategy first.',
        )

    # TODO: Delete via repository (cascade delete related data)
    await strategy.delete()


@strategies_router.post(
    '/{strategy_id}/start',
    response_model=TradingStrategyDocument,
    summary='Start trading strategy',
    description='Activate a trading strategy to begin automated execution',
)
async def start_strategy(strategy_id: UUID) -> TradingStrategyDocument:
    """
    Start strategy execution (T046).

    Args:
        strategy_id: Unique strategy identifier

    Returns:
        Strategy with updated status (ACTIVE)

    Raises:
        HTTPException 404: Strategy not found
        HTTPException 409: Invalid state transition
        HTTPException 500: Internal server error
    """
    strategy = await TradingStrategyDocument.find_one(TradingStrategyDocument.strategy_id == strategy_id)

    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Strategy {strategy_id} not found')

    # Validate state transition
    try:
        strategy.update_status(StrategyStatusEnum.ACTIVE)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    # TODO: Use StrategyManager service to start execution
    await strategy.save()

    return strategy


@strategies_router.post(
    '/{strategy_id}/stop',
    response_model=TradingStrategyDocument,
    summary='Stop trading strategy',
    description='Halt a trading strategy and close all open positions',
)
async def stop_strategy(strategy_id: UUID) -> TradingStrategyDocument:
    """
    Stop strategy execution (T047).

    Args:
        strategy_id: Unique strategy identifier

    Returns:
        Strategy with updated status (STOPPED)

    Raises:
        HTTPException 404: Strategy not found
        HTTPException 500: Internal server error
    """
    strategy = await TradingStrategyDocument.find_one(TradingStrategyDocument.strategy_id == strategy_id)

    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Strategy {strategy_id} not found')

    # TODO: Use StrategyManager service to stop execution and close positions
    strategy.update_status(StrategyStatusEnum.STOPPED)
    await strategy.save()

    return strategy


@strategies_router.post(
    '/{strategy_id}/pause',
    response_model=TradingStrategyDocument,
    summary='Pause trading strategy',
    description='Temporarily halt strategy execution without closing positions',
)
async def pause_strategy(strategy_id: UUID) -> TradingStrategyDocument:
    """
    Pause strategy execution (T048).

    Args:
        strategy_id: Unique strategy identifier

    Returns:
        Strategy with updated status (PAUSED)

    Raises:
        HTTPException 404: Strategy not found
        HTTPException 500: Internal server error
    """
    strategy = await TradingStrategyDocument.find_one(TradingStrategyDocument.strategy_id == strategy_id)

    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Strategy {strategy_id} not found')

    # TODO: Use StrategyManager service to pause execution
    strategy.update_status(StrategyStatusEnum.PAUSED)
    await strategy.save()

    return strategy

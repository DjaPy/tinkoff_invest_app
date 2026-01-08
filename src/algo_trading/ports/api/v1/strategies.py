"""
Strategies API endpoints - Hexagonal Architecture Inbound Port.

REST API endpoints for managing trading strategies.
Following FastAPI patterns and RFC7807 error handling.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.users.adapters.dto_models.users import UserData
from src.users.services.auth import get_current_active_user
from src.algo_trading.adapters.repositories.strategy_repository import (
    InvalidStateTransitionError,
    StrategyRepository,
)
from src.algo_trading.adapters.repositories.tinkoff_account_repository import (
    TinkoffAccountRepository,
)
from src.algo_trading.enums import StrategyStatusEnum
from src.algo_trading.adapters.models.strategy import (
    TinkoffAccountType,
    TradingStrategyDocument,
)
from src.algo_trading.ports.api.v1.schemas.strategies_schema import (
    CreateStrategyRequestSchema,
    StrategyListResponseSchema,
    TradingStrategyResponseSchema,
    UpdateStrategyRequestSchema,
)

strategies_router = APIRouter(
    prefix='/api/v1/strategies',
    tags=['Trading Strategies'],
    dependencies=[Depends(get_current_active_user)],
)


@strategies_router.post(
    '/',
    response_model=TradingStrategyResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary='Create new trading strategy',
    description='Create a new algorithmic trading strategy with configuration and risk controls',
)
async def create_strategy(
    request: CreateStrategyRequestSchema,
    current_user: UserData = Depends(get_current_active_user),
) -> TradingStrategyResponseSchema:
    """
    Create a new trading strategy (T042).

    Args:
        request: Strategy creation request with parameters and risk controls
        current_user: Authenticated user from JWT token

    Returns:
        Created strategy with unique ID and inactive status

    Raises:
        HTTPException 422: Validation error in request data
        HTTPException 500: Internal server error
    """
    strategy = await StrategyRepository.create_from_request(
        name=request.name,
        strategy_type=request.strategy_type,
        parameters=request.parameters,
        risk_controls=request.risk_controls,
        created_by=current_user.user_id,
        tinkoff_account_type=request.tinkoff_account_type,
    )

    return TradingStrategyResponseSchema.from_document(strategy)


@strategies_router.get(
    '/',
    response_model=StrategyListResponseSchema,
    summary='List all trading strategies',
    description='Retrieve all trading strategies for the authenticated user',
)
async def list_strategies(
    current_user: UserData = Depends(get_current_active_user),
) -> StrategyListResponseSchema:
    """
    List all trading strategies (T043).

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        List of strategies with total count

    Raises:
        HTTPException 500: Internal server error
    """
    strategies = await StrategyRepository.find_all(created_by=current_user.user_id)

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
    strategy = await StrategyRepository.find_by_id(strategy_id)

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategy {strategy_id} not found',
        )

    return strategy


@strategies_router.put(
    '/{strategy_id}',
    response_model=TradingStrategyResponseSchema,
    summary='Update trading strategy',
    description='Update strategy configuration and risk controls',
)
async def update_strategy(strategy_id: UUID, body: UpdateStrategyRequestSchema) -> TradingStrategyResponseSchema:
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
    strategy = await StrategyRepository.update_strategy(
        strategy_id=strategy_id,
        update_data=body,
    )

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategy {strategy_id} not found',
        )

    return TradingStrategyResponseSchema.from_document(strategy)


@strategies_router.delete(
    '/{strategy_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Delete trading strategy',
    description='Delete a trading strategy and all associated data',
)
async def delete_strategy(strategy_id: UUID) -> None:
    """
    Delete strategy.

    Args:
        strategy_id: Unique strategy identifier

    Raises:
        HTTPException 404: Strategy not found
        HTTPException 409: Cannot delete active strategy
        HTTPException 500: Internal server error
    """
    strategy = await StrategyRepository.find_by_id(strategy_id)

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategy {strategy_id} not found',
        ) from None

    if strategy.status == StrategyStatusEnum.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Cannot delete active strategy. Stop the strategy first.',
        ) from None

    await StrategyRepository.delete(strategy_id)


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
    try:
        return await StrategyRepository.start_strategy(strategy_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategy {strategy_id} not found',
        ) from err
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


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
        HTTPException 409: Invalid state transition
        HTTPException 500: Internal server error
    """
    try:
        return await StrategyRepository.stop_strategy(strategy_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategy {strategy_id} not found',
        ) from err
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


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
        HTTPException 409: Invalid state transition
        HTTPException 500: Internal server error
    """
    try:
        return await StrategyRepository.pause_strategy(strategy_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategy {strategy_id} not found',
        ) from err
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@strategies_router.post(
    '/{strategy_id}/clone-to-sandbox',
    response_model=TradingStrategyResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary='Clone strategy to sandbox',
    description='Create a sandbox copy of strategy for safe parameter testing',
)
async def clone_strategy_to_sandbox(
    strategy_id: UUID,
    current_user: UserData = Depends(get_current_active_user),
) -> TradingStrategyResponseSchema:
    """
    Clone strategy to user's default sandbox account.

    Creates a copy of the strategy with same parameters but linked
    to sandbox account. Useful for A/B testing parameter changes safely.

    Args:
        strategy_id: Source strategy UUID to clone
        current_user: Authenticated user from JWT token

    Returns:
        Cloned strategy with new UUID, inactive status, sandbox account

    Raises:
        HTTPException 404: Strategy not found or no default sandbox account
        HTTPException 403: User doesn't own the strategy
        HTTPException 500: Internal server error
    """
    source_strategy = await StrategyRepository.find_by_id(strategy_id)
    if not source_strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Strategy {strategy_id} not found',
        )

    if source_strategy.created_by != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You do not own this strategy',
        )

    sandbox_account = await TinkoffAccountRepository.get_default_account(
        user_id=current_user.user_id,
        account_type=TinkoffAccountType.SANDBOX,
    )

    if not sandbox_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No default sandbox account found. Create a sandbox account first.',
        )

    try:
        cloned_strategy = await StrategyRepository.clone_to_sandbox(
            strategy_id=strategy_id,
            sandbox_account=sandbox_account,
        )

        return TradingStrategyResponseSchema.from_document(cloned_strategy)

    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err

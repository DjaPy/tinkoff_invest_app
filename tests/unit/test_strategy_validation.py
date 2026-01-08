"""Unit tests for trading strategy validation (T079).

Tests cover:
1. Pydantic validation of strategy parameters (Momentum, Mean Reversion, Arbitrage, Market Making)
2. Risk controls validation
3. Status transition validation
4. Parameter type matching validation

These tests focus on Pydantic model validation without infrastructure dependencies.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.algo_trading.adapters.models.strategy import (
    MeanReversionParameters,
    MomentumParameters,
    RiskControls,
    TinkoffAccountType,
    TradingStrategyDocument,
)
from src.algo_trading.enums import StrategyStatusEnum, StrategyTypeEnum


async def test_inactive_to_active_transition_allowed(create_tinkoff_account):
    """Test INACTIVE → ACTIVE transition is allowed."""

    user_id = uuid4()
    tinkoff_account = await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)
    strategy = TradingStrategyDocument(
        name='Test Strategy',
        strategy_type=StrategyTypeEnum.MOMENTUM,
        status=StrategyStatusEnum.INACTIVE,
        parameters={
            'lookback_period': 50,
            'momentum_threshold': 0.5,
            'instruments': ['AAPL'],
            'position_size': 1000.0,
        },
        risk_controls=RiskControls(
            max_position_size=Decimal('100000.00'),
            max_portfolio_value=Decimal('1000000.00'),
            stop_loss_percent=Decimal('0.05'),
            max_drawdown_percent=Decimal('0.15'),
            daily_loss_limit=Decimal('10000.00'),
            max_orders_per_day=100,
            trading_hours_start='09:30:00',
            trading_hours_end='16:00:00',
        ),
        created_by=user_id,
        tinkoff_account=tinkoff_account,
    )

    assert strategy.can_transition_to(StrategyStatusEnum.ACTIVE) is True

    strategy.update_status(StrategyStatusEnum.ACTIVE)
    assert strategy.status == StrategyStatusEnum.ACTIVE


async def test_active_to_paused_transition_allowed(create_tinkoff_account):
    """Test ACTIVE → PAUSED transition is allowed."""
    user_id = uuid4()
    tinkoff_account = await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)
    strategy = TradingStrategyDocument(
        name='Test Strategy',
        strategy_type=StrategyTypeEnum.MOMENTUM,
        status=StrategyStatusEnum.ACTIVE,
        parameters={
            'lookback_period': 50,
            'momentum_threshold': 0.5,
            'instruments': ['AAPL'],
            'position_size': 1000.0,
        },
        risk_controls=RiskControls(
            max_position_size=Decimal('100000.00'),
            max_portfolio_value=Decimal('1000000.00'),
            stop_loss_percent=Decimal('0.05'),
            max_drawdown_percent=Decimal('0.15'),
            daily_loss_limit=Decimal('10000.00'),
            max_orders_per_day=100,
            trading_hours_start='09:30:00',
            trading_hours_end='16:00:00',
        ),
        created_by=user_id,
        tinkoff_account=tinkoff_account,
    )

    assert strategy.can_transition_to(StrategyStatusEnum.PAUSED) is True


async def test_inactive_to_paused_transition_rejected(create_tinkoff_account):
    """Test INACTIVE → PAUSED transition is rejected."""
    user_id = uuid4()
    tinkoff_account = await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)
    strategy = TradingStrategyDocument(
        name='Test Strategy',
        strategy_type=StrategyTypeEnum.MOMENTUM,
        status=StrategyStatusEnum.INACTIVE,
        parameters={
            'lookback_period': 50,
            'momentum_threshold': 0.5,
            'instruments': ['AAPL'],
            'position_size': 1000.0,
        },
        risk_controls=RiskControls(
            max_position_size=Decimal('100000.00'),
            max_portfolio_value=Decimal('1000000.00'),
            stop_loss_percent=Decimal('0.05'),
            max_drawdown_percent=Decimal('0.15'),
            daily_loss_limit=Decimal('10000.00'),
            max_orders_per_day=100,
            trading_hours_start='09:30:00',
            trading_hours_end='16:00:00',
        ),
        created_by=user_id,
        tinkoff_account=tinkoff_account,
    )

    assert strategy.can_transition_to(StrategyStatusEnum.PAUSED) is False

    with pytest.raises(ValueError) as exc_info:
        strategy.update_status(StrategyStatusEnum.PAUSED)

    assert 'Invalid status transition' in str(exc_info.value)


async def test_active_to_inactive_transition_rejected(create_tinkoff_account):
    """Test ACTIVE → INACTIVE transition is rejected."""
    user_id = uuid4()
    tinkoff_account = await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)
    strategy = TradingStrategyDocument(
        name='Test Strategy',
        strategy_type=StrategyTypeEnum.MOMENTUM,
        status=StrategyStatusEnum.ACTIVE,
        parameters={
            'lookback_period': 50,
            'momentum_threshold': 0.5,
            'instruments': ['AAPL'],
            'position_size': 1000.0,
        },
        risk_controls=RiskControls(
            max_position_size=Decimal('100000.00'),
            max_portfolio_value=Decimal('1000000.00'),
            stop_loss_percent=Decimal('0.05'),
            max_drawdown_percent=Decimal('0.15'),
            daily_loss_limit=Decimal('10000.00'),
            max_orders_per_day=100,
            trading_hours_start='09:30:00',
            trading_hours_end='16:00:00',
        ),
        created_by=user_id,
        tinkoff_account=tinkoff_account,
    )

    assert strategy.can_transition_to(StrategyStatusEnum.INACTIVE) is False


async def test_error_to_inactive_transition_allowed(create_tinkoff_account):
    """Test ERROR → INACTIVE transition is allowed."""
    user_id = uuid4()
    tinkoff_account = await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)
    strategy = TradingStrategyDocument(
        name='Test Strategy',
        strategy_type=StrategyTypeEnum.MOMENTUM,
        status=StrategyStatusEnum.ERROR,
        parameters={
            'lookback_period': 50,
            'momentum_threshold': 0.5,
            'instruments': ['AAPL'],
            'position_size': 1000.0,
        },
        risk_controls=RiskControls(
            max_position_size=Decimal('100000.00'),
            max_portfolio_value=Decimal('1000000.00'),
            stop_loss_percent=Decimal('0.05'),
            max_drawdown_percent=Decimal('0.15'),
            daily_loss_limit=Decimal('10000.00'),
            max_orders_per_day=100,
            trading_hours_start='09:30:00',
            trading_hours_end='16:00:00',
        ),
        created_by=user_id,
        tinkoff_account=tinkoff_account,
    )

    assert strategy.can_transition_to(StrategyStatusEnum.INACTIVE) is True


async def test_momentum_strategy_validates_parameter_type(create_tinkoff_account):
    """Test Momentum strategy accepts correct parameter type."""
    user_id = uuid4()
    tinkoff_account = await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)
    strategy = TradingStrategyDocument(
        name='Test Momentum Strategy',
        strategy_type=StrategyTypeEnum.MOMENTUM,
        parameters={
            'lookback_period': 50,
            'momentum_threshold': 0.5,
            'instruments': ['AAPL'],
            'position_size': 1000.0,
        },
        risk_controls=RiskControls(
            max_position_size=Decimal('100000.00'),
            max_portfolio_value=Decimal('1000000.00'),
            stop_loss_percent=Decimal('0.05'),
            max_drawdown_percent=Decimal('0.15'),
            daily_loss_limit=Decimal('10000.00'),
            max_orders_per_day=100,
            trading_hours_start='09:30:00',
            trading_hours_end='16:00:00',
        ),
        created_by=user_id,
        tinkoff_account=tinkoff_account,
    )

    assert strategy.strategy_type == StrategyTypeEnum.MOMENTUM
    assert isinstance(strategy.parameters, MomentumParameters)


async def test_mean_reversion_strategy_validates_parameter_type(create_tinkoff_account):
    """Test Mean Reversion strategy accepts correct parameter type."""
    user_id = uuid4()
    tinkoff_account = await create_tinkoff_account(user_id=user_id, account_type=TinkoffAccountType.SANDBOX)
    strategy = TradingStrategyDocument(
        name='Test Mean Reversion Strategy',
        strategy_type=StrategyTypeEnum.MEAN_REVERSION,
        parameters={
            'moving_average_period': 20,
            'std_dev_threshold': 2.0,
            'instruments': ['AAPL', 'MSFT'],
        },
        risk_controls=RiskControls(
            max_position_size=Decimal('100000.00'),
            max_portfolio_value=Decimal('1000000.00'),
            stop_loss_percent=Decimal('0.05'),
            max_drawdown_percent=Decimal('0.15'),
            daily_loss_limit=Decimal('10000.00'),
            max_orders_per_day=100,
            trading_hours_start='09:30:00',
            trading_hours_end='16:00:00',
        ),
        created_by=user_id,
        tinkoff_account=tinkoff_account,
    )

    assert strategy.strategy_type == StrategyTypeEnum.MEAN_REVERSION
    assert isinstance(strategy.parameters, MeanReversionParameters)


async def test_empty_strategy_name_rejected():
    """Test empty strategy name raises validation error."""
    with pytest.raises(ValidationError):
        TradingStrategyDocument(
            name='',
            strategy_type=StrategyTypeEnum.MOMENTUM,
            parameters={
                'lookback_period': 50,
                'momentum_threshold': 0.5,
                'instruments': ['AAPL'],
                'position_size': 1000.0,
            },
            risk_controls=RiskControls(
                max_position_size=Decimal('100000.00'),
                max_portfolio_value=Decimal('1000000.00'),
                stop_loss_percent=Decimal('0.05'),
                max_drawdown_percent=Decimal('0.15'),
                daily_loss_limit=Decimal('10000.00'),
                max_orders_per_day=100,
                trading_hours_start='09:30:00',
                trading_hours_end='16:00:00',
            ),
            created_by=uuid4(),
        )


async def test_strategy_name_too_long_rejected(create_tinkoff_account):
    """Test strategy name exceeding 200 chars raises validation error."""
    with pytest.raises(ValidationError):
        TradingStrategyDocument(
            name='A' * 201,
            strategy_type=StrategyTypeEnum.MOMENTUM,
            parameters={
                'lookback_period': 50,
                'momentum_threshold': 0.5,
                'instruments': ['AAPL'],
                'position_size': 1000.0,
            },
            risk_controls=RiskControls(
                max_position_size=Decimal('100000.00'),
                max_portfolio_value=Decimal('1000000.00'),
                stop_loss_percent=Decimal('0.05'),
                max_drawdown_percent=Decimal('0.15'),
                daily_loss_limit=Decimal('10000.00'),
                max_orders_per_day=100,
                trading_hours_start='09:30:00',
                trading_hours_end='16:00:00',
            ),
            created_by=uuid4(),
        )

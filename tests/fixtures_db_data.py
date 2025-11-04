import uuid
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from typing import Any, Callable

import pytest

from algo_trading.enums import OrderSideEnum, OrderStatusEnum, OrderTypeEnum
from src.algo_trading.adapters.models import (
    ArbitrageParameters,
    MarketMakingParameters,
    MeanReversionParameters,
    MomentumParameters,
    RiskControls,
    StrategyStatusEnum,
    StrategyTypeEnum,
    TradeOrderDocument,
    TradingSessionDocument,
    TradingStrategyDocument,
)


@pytest.fixture
def create_risk_controls(get_session, fake, pydantic_generator_data) -> Callable:
    def _inner(**kwargs: dict[str, Any]) -> RiskControls:

        return RiskControls(
            max_position_size=kwargs.pop(
                'max_position_size', fake.pydecimal(left_digits=5, right_digits=2, positive=True),
            ),
            max_portfolio_value=kwargs.pop(
                'max_portfolio_value', fake.pydecimal(left_digits=5, right_digits=2, positive=True),
            ),
            stop_loss_percent=kwargs.pop(
                'stop_loss_percent', fake.pydecimal(left_digits=0, right_digits=2, positive=True),
            ),
            max_drawdown_percent=kwargs.pop(
                'max_drawdown_percent', fake.pydecimal(left_digits=0, right_digits=2, positive=True),
            ),
            daily_loss_limit=kwargs.pop(
                'daily_loss_limit', fake.pydecimal(left_digits=5, right_digits=2, positive=True),
            ),
            max_orders_per_day=kwargs.pop('max_orders_per_day', fake.pyint(min_value=1, max_value=180)),
            trading_hours_start=kwargs.pop('trading_hours_start', '09:00:00'),
            trading_hours_end=kwargs.pop('trading_hours_end', '16:00:00'),
            enabled=kwargs.pop('enabled', True),
        )

    return _inner


@pytest.fixture
def create_trading_strategy(get_session, fake, pydantic_generator_data, create_risk_controls) -> Callable:
    async def _inner(**kwargs: dict[str, Any]) -> TradingStrategyDocument:
        if not (risk_controls := kwargs.pop('risk_controls', None)):
            risk_controls = create_risk_controls()

        strategy_type = kwargs.pop('strategy_type', fake.random.choice(list(StrategyTypeEnum)))

        if not (parameters := kwargs.pop('parameters', None)):
            parameters = _generate_parameters_for_strategy(strategy_type, fake)

        trading_strategy = TradingStrategyDocument(
            strategy_id=kwargs.pop('strategy_id',uuid.uuid4()),
            name=kwargs.pop('name',fake.name()),
            strategy_type=strategy_type,
            status=kwargs.pop('status', fake.random.choice(list(StrategyStatusEnum))),
            parameters=parameters,
            risk_controls=risk_controls,
            created_at=kwargs.pop('created_at', datetime.now(tz=UTC)),
            updated_at=kwargs.pop('updated_at', datetime.now(tz=UTC)),
            created_by=kwargs.pop('created_by', uuid.uuid4()),
        )
        await trading_strategy.insert()
        return trading_strategy
    return _inner


def _generate_parameters_for_strategy(
    strategy_type: StrategyTypeEnum, fake,
) -> MomentumParameters | MeanReversionParameters | ArbitrageParameters | MarketMakingParameters:
    """Generate valid parameters for a given strategy type."""

    if strategy_type == StrategyTypeEnum.MOMENTUM:
        return MomentumParameters(
            lookback_period=fake.pyint(min_value=1, max_value=200),
            momentum_threshold=fake.random.uniform(0.1, 0.99),
            instruments=[fake.word() for _ in range(fake.pyint(min_value=1, max_value=5))],
            position_size=float(fake.pydecimal(left_digits=5, right_digits=2, positive=True)),
        )
    if strategy_type == StrategyTypeEnum.MEAN_REVERSION:
        return MeanReversionParameters(
            moving_average_period=fake.pyint(min_value=5, max_value=200),
            std_dev_threshold=fake.random.uniform(0.1, 4.99),
            instruments=[fake.word() for _ in range(fake.pyint(min_value=1, max_value=5))],
        )
    if strategy_type == StrategyTypeEnum.ARBITRAGE:
        return ArbitrageParameters(
            instrument_pairs=[[fake.word(), fake.word()] for _ in range(fake.pyint(min_value=1, max_value=3))],
            spread_threshold=float(fake.pydecimal(left_digits=2, right_digits=4, positive=True)),
        )
    if strategy_type == StrategyTypeEnum.MARKET_MAKING:
        return MarketMakingParameters(
            bid_ask_spread=float(fake.pydecimal(left_digits=2, right_digits=4, positive=True)),
            inventory_limits={
                fake.word(): fake.pyint(min_value=100, max_value=10000)
                for _ in range(fake.pyint(min_value=1, max_value=3))
            },
            instruments=[fake.word() for _ in range(fake.pyint(min_value=1, max_value=5))],
        )

    raise ValueError(f'Unknown strategy type: {strategy_type}')


@pytest.fixture
def create_trading_sessions(get_session, fake, pydantic_generator_data) -> Callable:
    async def _inner(**kwargs) -> TradingSessionDocument:
        # Generate defaults
        session_start = kwargs.pop('session_start', datetime.now(tz=UTC))
        session_end = kwargs.pop('session_end', session_start + timedelta(hours=8))  # 8 hour session

        starting_capital = kwargs.pop('starting_capital', Decimal('100000.00'))
        ending_capital = kwargs.pop(
            'ending_capital',
            starting_capital + fake.pydecimal(left_digits=4, right_digits=2, positive=False),
        )

        trading_session = TradingSessionDocument(
            strategy_id=kwargs.pop('strategy_id', uuid.uuid4()),
            session_start=session_start,
            session_end=session_end,
            orders_placed=kwargs.pop('orders_placed', 100),
            orders_filled=kwargs.pop('orders_filled', 40),
            orders_cancelled=kwargs.pop('orders_cancelled', 40),
            orders_rejected=kwargs.pop('orders_rejected', 20),
            total_commission=kwargs.pop('total_commission', Decimal('500.00')),
            realized_pnl=kwargs.pop('realized_pnl', ending_capital - starting_capital),
            starting_capital=starting_capital,
            ending_capital=ending_capital,
            max_drawdown_reached=kwargs.pop('max_drawdown_reached', Decimal('-0.05')),  # -5%
            risk_violations=kwargs.pop('risk_violations', 0),
        )
        await trading_session.insert()
        return trading_session
    return _inner


@pytest.fixture
def create_order(get_session, fake, pydantic_generator_data) -> Callable:
    async def _inner(**kwargs) -> TradeOrderDocument:

        side = kwargs.pop('side', fake.random.choice(list(OrderSideEnum)))
        order_type = kwargs.pop('order_type', OrderTypeEnum.MARKET)
        quantity = kwargs.pop('quantity', Decimal(str(fake.pyint(min_value=1, max_value=100))))
        price = kwargs.pop('price', Decimal(str(fake.pyfloat(min_value=100, max_value=1000, right_digits=2))))

        status = kwargs.pop('status', OrderStatusEnum.FILLED)
        filled_price = kwargs.pop('filled_price', price if status == OrderStatusEnum.FILLED else Decimal('0'))
        filled_quantity = kwargs.pop('filled_quantity', quantity if status == OrderStatusEnum.FILLED else Decimal('0'))
        filled_at = kwargs.pop('filled_at', datetime.now(tz=UTC) if status == OrderStatusEnum.FILLED else None)

        trade_order = TradeOrderDocument(
            order_id=kwargs.pop('order_id', uuid.uuid4()),
            strategy_id=kwargs.pop('strategy_id', uuid.uuid4()),
            session_id=kwargs.pop('session_id', uuid.uuid4()),
            correlation_id=kwargs.pop('correlation_id', uuid.uuid4()),
            instrument=kwargs.pop('instrument', fake.word().upper()),  # Random ticker
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price,
            status=status,
            submitted_at=kwargs.pop('submitted_at', datetime.now(tz=UTC)),
            filled_at=filled_at,
            filled_price=filled_price,
            filled_quantity=filled_quantity,
            commission=kwargs.pop('commission', Decimal('10.00')),
            external_order_id=kwargs.pop('external_order_id', None),
        )
        await trade_order.insert()
        return trade_order
    return _inner

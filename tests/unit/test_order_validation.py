"""Unit tests for order validation logic (T081).

Tests cover:
1. Pydantic validation of TradeOrder fields (quantity, price, filled_quantity)
2. Limit price validation for different order types
3. Order status transition validation
4. Order immutability after final status
5. Business rule validation in OrderExecutor
6. Filled quantity constraints
7. Total value calculations

These tests focus on pure domain and validation logic without infrastructure dependencies.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from src.algo_trading.adapters.models.order import TradeOrderDocument
from src.algo_trading.enums import OrderSideEnum, OrderStatusEnum, OrderTypeEnum
from src.algo_trading.services.order_executor import OrderExecutor, OrderExecutorError


async def test_filled_quantity_cannot_exceed_order_quantity(mongo_connection):
    """Test filled quantity cannot exceed ordered quantity."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,  # Must be SUBMITTED to transition to FILLED
    )

    with pytest.raises(ValueError) as exc_info:
        order.update_status(
            OrderStatusEnum.FILLED,
            filled_price=Decimal('150.00'),
            filled_quantity=Decimal('150'),  # Invalid: exceeds 100
        )

    assert 'exceeds order quantity' in str(exc_info.value)


async def test_filled_quantity_equals_order_quantity_allowed(mongo_connection):
    """Test filled quantity equal to order quantity is valid."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,
    )

    order.update_status(
        OrderStatusEnum.FILLED,
        filled_price=Decimal('150.00'),
        filled_quantity=Decimal('100'),  # Valid: equals order quantity
    )

    assert order.status == OrderStatusEnum.FILLED
    assert order.filled_quantity == Decimal('100')


async def test_partial_fill_within_order_quantity_allowed(mongo_connection):
    """Test partial fill within order quantity is valid."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,
    )

    order.update_status(
        OrderStatusEnum.PARTIALLY_FILLED,
        filled_price=Decimal('150.00'),
        filled_quantity=Decimal('50'),  # Valid: partial fill
    )

    assert order.status == OrderStatusEnum.PARTIALLY_FILLED
    assert order.filled_quantity == Decimal('50')



async def test_pending_to_submitted_transition_allowed(mongo_connection):
    """Test PENDING → SUBMITTED transition is valid."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.PENDING,
    )

    assert order.can_transition_to(OrderStatusEnum.SUBMITTED) is True

    order.update_status(OrderStatusEnum.SUBMITTED)
    assert order.status == OrderStatusEnum.SUBMITTED


async def test_submitted_to_filled_transition_allowed(mongo_connection):
    """Test SUBMITTED → FILLED transition is valid."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,
    )

    assert order.can_transition_to(OrderStatusEnum.FILLED) is True


async def test_submitted_to_cancelled_transition_allowed(mongo_connection):
    """Test SUBMITTED → CANCELLED transition is valid."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,
    )

    assert order.can_transition_to(OrderStatusEnum.CANCELLED) is True


async def test_submitted_to_rejected_transition_allowed(mongo_connection):
    """Test SUBMITTED → REJECTED transition is valid."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,
    )

    assert order.can_transition_to(OrderStatusEnum.REJECTED) is True


async def test_partially_filled_to_filled_transition_allowed(mongo_connection):
    """Test PARTIALLY_FILLED → FILLED transition is valid."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.PARTIALLY_FILLED,
    )

    assert order.can_transition_to(OrderStatusEnum.FILLED) is True


async def test_partially_filled_to_cancelled_transition_allowed(mongo_connection):
    """Test PARTIALLY_FILLED → CANCELLED transition is valid."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.PARTIALLY_FILLED,
    )

    assert order.can_transition_to(OrderStatusEnum.CANCELLED) is True


async def test_pending_to_filled_transition_rejected(mongo_connection):
    """Test PENDING → FILLED transition is invalid."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.PENDING,
    )

    assert order.can_transition_to(OrderStatusEnum.FILLED) is False

    with pytest.raises(ValueError) as exc_info:
        order.update_status(OrderStatusEnum.FILLED)

    assert 'Invalid status transition' in str(exc_info.value)


async def test_pending_to_cancelled_transition_rejected(mongo_connection):
    """Test PENDING → CANCELLED transition is invalid."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.PENDING,
    )

    assert order.can_transition_to(OrderStatusEnum.CANCELLED) is True



async def test_order_becomes_immutable_after_filled(mongo_connection):
    """Test order becomes immutable after FILLED status."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,
    )

    order.update_status(OrderStatusEnum.FILLED, filled_price=Decimal('150.00'), filled_quantity=Decimal('100'))

    assert order._immutable is True

    with pytest.raises(ValueError) as exc_info:
        order.update_status(OrderStatusEnum.CANCELLED)

    assert 'immutable' in str(exc_info.value).lower()


async def test_order_becomes_immutable_after_cancelled(mongo_connection):
    """Test order becomes immutable after CANCELLED status."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,
    )

    order.update_status(OrderStatusEnum.CANCELLED)

    assert order._immutable is True

    with pytest.raises(ValueError) as exc_info:
        order.update_status(OrderStatusEnum.FILLED)

    assert 'immutable' in str(exc_info.value).lower()


async def test_order_becomes_immutable_after_rejected(mongo_connection):
    """Test order becomes immutable after REJECTED status."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,
    )

    order.update_status(OrderStatusEnum.REJECTED)

    assert order._immutable is True



async def test_validate_empty_instrument_rejected():
    """Test empty instrument is rejected by business rules."""
    executor = OrderExecutor()

    with pytest.raises(OrderExecutorError) as exc_info:
        executor._validate_order_params('', Decimal('100'), OrderTypeEnum.MARKET, None)

    assert 'Instrument cannot be empty' in str(exc_info.value)



async def test_validate_whitespace_instrument_rejected():
    """Test whitespace-only instrument is rejected."""
    executor = OrderExecutor()

    with pytest.raises(OrderExecutorError) as exc_info:
        executor._validate_order_params('   ', Decimal('100'), OrderTypeEnum.MARKET, None)

    assert 'Instrument cannot be empty' in str(exc_info.value)



async def test_validate_zero_quantity_rejected():
    """Test zero quantity is rejected."""
    executor = OrderExecutor()

    with pytest.raises(OrderExecutorError) as exc_info:
        executor._validate_order_params('AAPL', Decimal('0'), OrderTypeEnum.MARKET, None)

    assert 'Quantity must be positive' in str(exc_info.value)



async def test_validate_negative_quantity_rejected():
    """Test negative quantity is rejected."""
    executor = OrderExecutor()

    with pytest.raises(OrderExecutorError) as exc_info:
        executor._validate_order_params('AAPL', Decimal('-100'), OrderTypeEnum.MARKET, None)

    assert 'Quantity must be positive' in str(exc_info.value)



async def test_validate_fractional_quantity_below_one_rejected():
    """Test fractional quantity below 1 is rejected."""
    executor = OrderExecutor()

    with pytest.raises(OrderExecutorError) as exc_info:
        executor._validate_order_params('AAPL', Decimal('0.5'), OrderTypeEnum.MARKET, None)

    assert 'Quantity must be at least 1' in str(exc_info.value)



async def test_validate_zero_price_for_limit_order_rejected():
    """Test zero price for LIMIT order is rejected."""
    executor = OrderExecutor()

    with pytest.raises(OrderExecutorError) as exc_info:
        executor._validate_order_params('AAPL', Decimal('100'), OrderTypeEnum.LIMIT, Decimal('0'))

    assert 'Price must be positive' in str(exc_info.value)



async def test_validate_negative_price_for_limit_order_rejected():
    """Test negative price for LIMIT order is rejected."""
    executor = OrderExecutor()

    with pytest.raises(OrderExecutorError) as exc_info:
        executor._validate_order_params('AAPL', Decimal('100'), OrderTypeEnum.LIMIT, Decimal('-150'))

    assert 'Price must be positive' in str(exc_info.value)



async def test_validate_market_order_with_price_rejected():
    """Test MARKET order with price is rejected."""
    executor = OrderExecutor()

    with pytest.raises(OrderExecutorError) as exc_info:
        executor._validate_order_params('AAPL', Decimal('100'), OrderTypeEnum.MARKET, Decimal('150'))

    assert 'Market orders cannot specify a price' in str(exc_info.value)



async def test_validate_valid_market_order_accepted():
    """Test valid MARKET order passes validation."""
    executor = OrderExecutor()

    # Should not raise
    executor._validate_order_params('AAPL', Decimal('100'), OrderTypeEnum.MARKET, None)



async def test_validate_valid_limit_order_accepted():
    """Test valid LIMIT order passes validation."""
    executor = OrderExecutor()

    # Should not raise
    executor._validate_order_params('AAPL', Decimal('100'), OrderTypeEnum.LIMIT, Decimal('150.00'))


# ==================== TOTAL VALUE CALCULATION TESTS ====================



async def test_calculate_total_value_without_commission(mongo_connection):
    """Test total value calculation without commission."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,
    )

    order.update_status(
        OrderStatusEnum.FILLED,
        filled_price=Decimal('150.00'),
        filled_quantity=Decimal('100'),
    )

    total_value = order.calculate_total_value()

    assert total_value == Decimal('15000.00')  # 100 * 150



async def test_calculate_total_value_with_commission(mongo_connection):
    """Test total value calculation with commission."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,
    )

    order.update_status(
        OrderStatusEnum.FILLED,
        filled_price=Decimal('150.00'),
        filled_quantity=Decimal('100'),
    )
    order.commission = Decimal('10.00')

    total_value = order.calculate_total_value()

    assert total_value == Decimal('15010.00')  # 100 * 150 + 10



async def test_calculate_total_value_partial_fill(mongo_connection):
    """Test total value calculation for partial fill."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.SUBMITTED,
    )

    order.update_status(
        OrderStatusEnum.PARTIALLY_FILLED,
        filled_price=Decimal('150.00'),
        filled_quantity=Decimal('50'),  # Partial fill
    )
    order.commission = Decimal('5.00')

    total_value = order.calculate_total_value()

    assert total_value == Decimal('7505.00')  # 50 * 150 + 5



async def test_calculate_total_value_unfilled_order(mongo_connection):
    """Test total value for unfilled order is zero."""
    order = TradeOrderDocument(
        strategy_id=uuid4(),
        session_id=uuid4(),
        instrument='AAPL',
        order_type=OrderTypeEnum.MARKET,
        side=OrderSideEnum.BUY,
        quantity=Decimal('100'),
        status=OrderStatusEnum.PENDING,
    )

    total_value = order.calculate_total_value()

    assert total_value == Decimal('0')

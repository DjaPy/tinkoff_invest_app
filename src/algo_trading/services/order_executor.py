"""OrderExecutor Service - Application Use Case Layer.

Orchestrates order placement, risk validation, and execution tracking.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from src.algo_trading.adapters.dto_models.order_dto import OrderDTO
from src.algo_trading.adapters.models import (
    OrderSide,
    OrderStatus,
    OrderType,
    PortfolioPosition,
    TradeOrder,
    TradingSession,
)
from src.algo_trading.domain.risk.risk_evaluator import OrderProposal, PositionRisk, RiskEvaluator, RiskLimits


class OrderExecutorError(Exception):
    """Order execution operation failed."""


class OrderExecutor:
    """
    Application service for order execution.

    Handles pre-trade risk validation, order placement, and tracking.
    """

    def __init__(self, risk_evaluator: RiskEvaluator | None = None) -> None:
        """
        Initialize OrderExecutor.

        Args:
            risk_evaluator: Domain service for risk evaluation (optional)
        """
        self.risk_evaluator = risk_evaluator or RiskEvaluator()

    async def place_order(
        self,
        order: OrderDTO,
        risk_limits: RiskLimits | None = None,
        current_risk: PositionRisk | None = None,
    ) -> TradeOrder:
        """
        Place a new order with risk validation.

        Args:
            order: OrderDTO
            risk_limits: Risk control limits (if None, skip validation)
            current_risk: Current portfolio risk (if None, skip validation)

        Returns:
            Created TradeOrder

        Raises:
            OrderExecutorError: If risk validation fails or order invalid
        """
        # Business rule validations
        self._validate_order_params(order.instrument, order.quantity, order.order_type, order.limit_price)

        # Validate price for limit orders
        if (
            order.order_type in {OrderType.LIMIT, OrderType.STOP_LOSS, OrderType.TAKE_PROFIT}
            and order.limit_price is None
        ):
            raise OrderExecutorError(f'{order.order_type} orders require a price')

        # Pre-trade risk validation
        if risk_limits and current_risk:
            estimated_price = order.limit_price if order.limit_price else await self._get_market_price(order.instrument)

            order_proposal = OrderProposal(
                instrument=order.instrument,
                quantity=order.quantity,
                estimated_price=estimated_price,
                side=order.side.value,
            )

            risk_result = self.risk_evaluator.evaluate_order(
                order=order_proposal,
                current_risk=current_risk,
                limits=risk_limits,
            )

            if not risk_result.approved:
                raise OrderExecutorError(f'Order rejected by risk controls: {risk_result.reason}')

        # Create order
        order = TradeOrder(
            strategy_id=order.strategy_id,
            session_id=order.session_id,
            instrument=order.instrument,
            order_type=order.order_type,
            side=order.side,
            quantity=order.quantity,
            price=order.limit_price,
        )

        await order.insert()

        # Record order in session
        session = await TradingSession.get(order.session_id)
        if session:
            session.record_order('pending')
            await session.save()

        return order

    async def submit_order(self, order_id: UUID, external_order_id: str) -> TradeOrder:
        """
        Mark order as submitted to broker.

        Args:
            order_id: Order UUID
            external_order_id: Broker's order identifier

        Returns:
            Updated order

        Raises:
            OrderExecutorError: If order not found or invalid transition
        """
        order = await TradeOrder.find_one(TradeOrder.order_id == order_id)
        if not order:
            raise OrderExecutorError(f'Order {order_id} not found')

        try:
            order.update_status(OrderStatus.SUBMITTED, external_order_id=external_order_id)
            await order.save()
        except ValueError as e:
            raise OrderExecutorError(f'Failed to submit order: {e}') from e

        return order

    async def fill_order(
        self,
        order_id: UUID,
        filled_price: Decimal,
        filled_quantity: Decimal,
        commission: Decimal = Decimal('0'),
    ) -> tuple[TradeOrder, PortfolioPosition | None]:
        """
        Mark order as filled and update portfolio position.

        Args:
            order_id: Order UUID
            filled_price: Execution price
            filled_quantity: Filled quantity
            commission: Trading commission

        Returns:
            Tuple of (updated_order, updated_position)

        Raises:
            OrderExecutorError: If operation fails
        """
        order = await TradeOrder.find_one(TradeOrder.order_id == order_id)
        if not order:
            raise OrderExecutorError(f'Order {order_id} not found')

        try:
            # Determine final status
            status = OrderStatus.FILLED if filled_quantity == order.quantity else OrderStatus.PARTIALLY_FILLED

            order.update_status(status, filled_price=filled_price, filled_quantity=filled_quantity)
            order.commission = commission
            await order.save()

            # Update position
            position = await self._update_position(order, filled_price, filled_quantity)

            # Update session
            session = await TradingSession.get(order.session_id)
            if session:
                session.record_order('filled')
                session.add_commission(commission)
                await session.save()

            return order, position

        except ValueError as e:
            raise OrderExecutorError(f'Failed to fill order: {e}') from e

    async def cancel_order(self, order_id: UUID) -> TradeOrder:
        """
        Cancel order before execution.

        Args:
            order_id: Order UUID

        Returns:
            Updated order

        Raises:
            OrderExecutorError: If cannot cancel
        """
        order = await TradeOrder.find_one(TradeOrder.order_id == order_id)
        if not order:
            raise OrderExecutorError(f'Order {order_id} not found')

        try:
            order.update_status(OrderStatus.CANCELLED)
            await order.save()

            # Update session
            session = await TradingSession.get(order.session_id)
            if session:
                session.record_order('cancelled')
                await session.save()

        except ValueError as e:
            raise OrderExecutorError(f'Failed to cancel order: {e}') from e

        return order

    async def reject_order(self, order_id: UUID, reason: str) -> TradeOrder:
        """
        Mark order as rejected by broker.

        Args:
            order_id: Order UUID
            reason: Rejection reason

        Returns:
            Updated order

        Raises:
            OrderExecutorError: If operation fails
        """
        order = await TradeOrder.find_one(TradeOrder.order_id == order_id)
        if not order:
            raise OrderExecutorError(f'Order {order_id} not found')

        try:
            order.update_status(OrderStatus.REJECTED)
            await order.save()

            # Update session
            session = await TradingSession.get(order.session_id)
            if session:
                session.record_order('rejected')
                await session.save()

        except ValueError as e:
            raise OrderExecutorError(f'Failed to reject order: {e}') from e

        return order

    async def get_order(self, order_id: UUID) -> TradeOrder:
        """
        Get order by ID.

        Args:
            order_id: Order UUID

        Returns:
            TradeOrder

        Raises:
            OrderExecutorError: If not found
        """
        order = await TradeOrder.find_one(TradeOrder.order_id == order_id)
        if not order:
            raise OrderExecutorError(f'Order {order_id} not found')

        return order

    async def list_orders(
        self,
        strategy_id: UUID | None = None,
        session_id: UUID | None = None,
        status: OrderStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TradeOrder]:
        """
        List orders with filtering.

        Args:
            strategy_id: Filter by strategy
            session_id: Filter by session
            status: Filter by status
            limit: Max results
            offset: Skip N results

        Returns:
            List of orders
        """
        query: dict[str, Any] = {}

        if strategy_id:
            query['strategy_id'] = strategy_id

        if session_id:
            query['session_id'] = session_id

        if status:
            query['status'] = status

        return await TradeOrder.find(query).skip(offset).limit(limit).to_list()

    async def _update_position(
        self,
        order: TradeOrder,
        filled_price: Decimal,
        filled_quantity: Decimal,
    ) -> PortfolioPosition | None:
        """
        Update portfolio position after order fill.

        Args:
            order: Filled order
            filled_price: Execution price
            filled_quantity: Filled quantity

        Returns:
            Updated position or None
        """
        # Find existing position
        position = await PortfolioPosition.find_one(
            PortfolioPosition.strategy_id == order.strategy_id,
            PortfolioPosition.instrument == order.instrument,
        )

        # Calculate position delta
        quantity_delta = filled_quantity if order.side == OrderSide.BUY else -filled_quantity

        if position:
            # Update existing position
            position.add_trade(quantity_delta, filled_price)
            await position.save()
        else:
            # Create new position
            position = PortfolioPosition(
                strategy_id=order.strategy_id,
                instrument=order.instrument,
                quantity=quantity_delta,
                average_price=filled_price,
                current_price=filled_price,
            )
            await position.insert()

        return position

    async def _get_market_price(self, instrument: str) -> Decimal:
        """
        Get current market price for instrument.

        Args:
            instrument: Trading instrument

        Returns:
            Market price

        Note:
            This is a placeholder. Real implementation would fetch from market data service.
        """
        # TODO: Integrate with MarketData service
        # For now, return placeholder
        return Decimal('100.00')

    def _validate_order_params(
        self,
        instrument: str,
        quantity: Decimal,
        order_type: OrderType,
        price: Decimal | None,
    ) -> None:
        """
        Validate order parameters against business rules.

        Args:
            instrument: Trading instrument
            quantity: Order quantity
            order_type: Type of order
            price: Limit price (if applicable)

        Raises:
            OrderExecutorError: If validation fails
        """
        if not instrument or not instrument.strip():
            raise OrderExecutorError('Instrument cannot be empty')

        if quantity <= 0:
            raise OrderExecutorError(f'Quantity must be positive, got {quantity}')

        if quantity < Decimal('1'):
            raise OrderExecutorError(f'Quantity must be at least 1, got {quantity}')

        if (
            order_type in {OrderType.LIMIT, OrderType.STOP_LOSS, OrderType.TAKE_PROFIT}
            and price is not None
            and price <= 0
        ):
            raise OrderExecutorError(f'Price must be positive, got {price}')

        if order_type == OrderType.MARKET and price is not None:
            raise OrderExecutorError('Market orders cannot specify a price')

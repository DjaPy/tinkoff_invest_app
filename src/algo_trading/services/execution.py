"""Order Execution Service via Tinkoff API.

Handles real order execution through Tinkoff Invest broker.
"""

from decimal import Decimal
from uuid import UUID

from src.algo_trading.adapters.models import OrderStatus, TradeOrder
from src.algo_trading.adapters.tinkoff_client import TinkoffInvestClient


class ExecutionError(Exception):
    """Order execution operation failed."""


class TinkoffExecutionService:
    """
    Service for executing orders via Tinkoff Invest API.

    Handles order placement, cancellation, and status tracking.
    """

    def __init__(self, tinkoff_client: TinkoffInvestClient) -> None:
        """
        Initialize execution service.

        Args:
            tinkoff_client: Tinkoff Invest API client
        """
        self.client = tinkoff_client
        self._figi_cache: dict[str, str] = {}

    async def _get_figi(self, ticker: str) -> str:
        """
        Get FIGI for ticker with caching.

        Args:
            ticker: Instrument ticker

        Returns:
            FIGI identifier

        Raises:
            ExecutionError: If FIGI lookup fails
        """
        if ticker in self._figi_cache:
            return self._figi_cache[ticker]

        try:
            instrument = await self.client.get_instrument_by_ticker(ticker)
            figi = instrument['figi']
            self._figi_cache[ticker] = figi
            return figi
        except Exception as e:
            raise ExecutionError(f'Failed to get FIGI for {ticker}: {e}') from e

    async def submit_order(self, order: TradeOrder) -> TradeOrder:
        """
        Submit order to Tinkoff Invest.

        Args:
            order: Order to submit

        Returns:
            Updated order with external_order_id

        Raises:
            ExecutionError: If submission fails
        """
        try:
            # Get FIGI for instrument
            figi = await self._get_figi(order.instrument)

            # Get instrument info for lot size
            instrument = await self.client.get_instrument_by_ticker(order.instrument)
            lot_size = instrument.get('lot', 1)

            # Calculate lots from quantity
            lots = int(order.quantity / lot_size)
            if lots == 0:
                lots = 1  # Minimum 1 lot

            # Submit order to Tinkoff
            response = await self.client.place_order(
                figi=figi,
                quantity=lots,
                order_type=order.order_type,
                side=order.side,
                price=order.price,
            )

            # Update order with external ID
            order.external_order_id = response['external_order_id']
            order.update_status(OrderStatus.SUBMITTED)
            await order.save()

            return order
        except Exception as e:
            # Mark order as rejected
            order.update_status(OrderStatus.REJECTED)
            await order.save()
            raise ExecutionError(f'Failed to submit order {order.order_id}: {e}') from e

    async def cancel_order(self, order: TradeOrder) -> TradeOrder:
        """
        Cancel order via Tinkoff Invest.

        Args:
            order: Order to cancel

        Returns:
            Updated order

        Raises:
            ExecutionError: If cancellation fails
        """
        if not order.external_order_id:
            raise ExecutionError(f'Order {order.order_id} has no external_order_id')

        try:
            # Cancel via Tinkoff API
            success = await self.client.cancel_order(order.external_order_id)

            if success:
                order.update_status(OrderStatus.CANCELLED)
                await order.save()

            return order
        except Exception as e:
            raise ExecutionError(f'Failed to cancel order {order.order_id}: {e}') from e

    async def check_order_status(self, order: TradeOrder) -> OrderStatus:
        """
        Check order status from Tinkoff.

        Args:
            order: Order to check

        Returns:
            Current order status

        Raises:
            ExecutionError: If status check fails

        Note:
            This is a placeholder. Full implementation would query
            Tinkoff API for order status updates.
        """
        if not order.external_order_id:
            return order.status

        # TODO: Implement actual status check via Tinkoff API

        return order.status

    async def get_execution_price(self, order: TradeOrder) -> Decimal | None:
        """
        Get execution price for filled order.

        Args:
            order: Order to check

        Returns:
            Execution price or None if not filled

        Raises:
            ExecutionError: If price check fails

        Note:
            This is a placeholder. Full implementation would query
            Tinkoff API for execution details.
        """
        if order.status != OrderStatus.FILLED:
            return None

        if order.filled_price:
            return order.filled_price

        # TODO: Implement actual execution price fetch via Tinkoff API
        return None

    async def sync_portfolio_positions(self, strategy_id: UUID) -> list[dict]:
        """
        Sync portfolio positions from Tinkoff.

        Args:
            strategy_id: Strategy ID to sync positions for

        Returns:
            List of synced positions

        Raises:
            ExecutionError: If sync fails
        """
        try:
            # Get portfolio from Tinkoff
            portfolio = await self.client.get_portfolio()

            synced_positions = []
            for position in portfolio['positions']:
                # Map FIGI back to ticker (reverse lookup)
                # TODO: Implement FIGI -> ticker mapping
                synced_positions.append(
                    {
                        'figi': position['figi'],
                        'quantity': position['quantity'],
                        'average_price': position['average_price'],
                        'current_price': position['current_price'],
                    },
                )

            return synced_positions
        except Exception as e:
            raise ExecutionError(f'Failed to sync portfolio positions: {e}') from e

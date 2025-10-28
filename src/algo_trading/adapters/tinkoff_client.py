"""Tinkoff Invest API Client Adapter - Hexagonal Architecture.

Adapter for Tinkoff Invest API integration using tinkoff-investments library.
"""

from decimal import Decimal
from typing import Any

from aiomisc import get_context
from tinkoff.invest import CandleInterval, InstrumentIdType, OrderDirection
from tinkoff.invest import OrderType as TinkoffOrderType
from tinkoff.invest import Quotation
from tinkoff.invest.async_services import AsyncServices
from tinkoff.invest.schemas import MoneyValue

from src.algo_trading.adapters.models import OrderSide, OrderType


class TinkoffClientError(Exception):
    """Tinkoff API client operation failed."""


def quotation_to_decimal(quotation: Quotation) -> Decimal:
    """
    Convert Tinkoff Quotation to Decimal.

    Args:
        quotation: Tinkoff Quotation object

    Returns:
        Decimal representation
    """
    return Decimal(str(quotation.units)) + Decimal(str(quotation.nano)) / Decimal('1000000000')


def money_value_to_decimal(money: MoneyValue) -> Decimal:
    """
    Convert Tinkoff MoneyValue to Decimal.

    Args:
        money: Tinkoff MoneyValue object

    Returns:
        Decimal representation
    """
    return Decimal(str(money.units)) + Decimal(str(money.nano)) / Decimal('1000000000')


def decimal_to_quotation(value: Decimal) -> Quotation:
    """
    Convert Decimal to Tinkoff Quotation.

    Args:
        value: Decimal value

    Returns:
        Tinkoff Quotation object
    """
    units = int(value)
    nano = int((value - units) * Decimal('1000000000'))
    return Quotation(units=units, nano=nano)


class TinkoffInvestClient:
    """
    Adapter for Tinkoff Invest API.

    Provides interface for trading operations via Tinkoff Invest API.
    Implements outbound port for external broker integration.
    """

    _client: AsyncServices | None = None

    def __init__(self, account_id: str, context_name: str) -> None:
        """
        Initialize Tinkoff Invest client.

        Args:
            context_name: AsyncClient into Tinkoff
        """
        self._account_id = account_id
        self._context_name = context_name

    async def init_client(self) -> AsyncServices:
        if self._client is None:
            self._client = await get_context()[self._context_name]
        raise TinkoffClientError('Not found tinkoff client')

    def __ensure_client(self) -> AsyncServices:
        """Ensure client is initialized."""
        if not self._client:
            raise TinkoffClientError('Client not initialized. Use as async context manager.')
        return self._client

    async def get_instrument_by_ticker(self, ticker: str) -> dict[str, Any]:
        """
        Get instrument information by ticker.

        Args:
            ticker: Instrument ticker (e.g., "AAPL", "SBER")

        Returns:
            Instrument details including FIGI

        Raises:
            TinkoffClientError: If instrument not found
        """
        client = self.__ensure_client()
        try:
            # Search for shares by ticker
            response = await client.instruments.share_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_TICKER, id=ticker)

            if not response.instrument:
                raise TinkoffClientError(f'Instrument {ticker} not found')

            instrument = response.instrument
            return {
                'figi': instrument.figi,
                'ticker': instrument.ticker,
                'name': instrument.name,
                'currency': instrument.currency,
                'lot': instrument.lot,
                'min_price_increment': quotation_to_decimal(instrument.min_price_increment),
            }
        except Exception as e:
            raise TinkoffClientError(f'Failed to get instrument {ticker}: {e}') from e

    async def get_last_price(self, figi: str) -> Decimal:
        """
        Get last traded price by FIGI.

        Args:
            figi: Financial Instrument Global Identifier

        Returns:
            Last traded price

        Raises:
            TinkoffClientError: If price fetch fails
        """
        client = self.__ensure_client()

        try:
            response = await client.market_data.get_last_prices(figi=[figi])

            if not response.last_prices:
                raise TinkoffClientError(f'No price data for FIGI {figi}')

            last_price = response.last_prices[0]
            return quotation_to_decimal(last_price.price)
        except Exception as e:
            raise TinkoffClientError(f'Failed to get last price for {figi}: {e}') from e

    async def get_market_price(self, ticker: str) -> Decimal:
        """
        Get current market price by ticker.

        Args:
            ticker: Instrument ticker

        Returns:
            Current market price

        Raises:
            TinkoffClientError: If price fetch fails
        """
        instrument = await self.get_instrument_by_ticker(ticker)
        return await self.get_last_price(instrument['figi'])

    async def place_order(
        self,
        figi: str,
        quantity: int,
        order_type: OrderType,
        side: OrderSide,
        price: Decimal = Decimal('0'),
    ) -> dict[str, Any]:
        """
        Place order via Tinkoff Invest API.

        Args:
            figi: Financial Instrument Global Identifier
            quantity: Order quantity in lots
            order_type: Order type (market, limit)
            side: Buy or sell
            price: Limit price (required for limit orders)

        Returns:
            Order execution details

        Raises:
            TinkoffClientError: If order placement fails
        """
        client = self.__ensure_client()

        if not self._account_id:
            raise TinkoffClientError('Account ID not set')

        try:
            # Map our order types to Tinkoff types
            tinkoff_order_type = (
                TinkoffOrderType.ORDER_TYPE_MARKET
                if order_type == OrderType.MARKET
                else TinkoffOrderType.ORDER_TYPE_LIMIT
            )

            direction = (
                OrderDirection.ORDER_DIRECTION_BUY if side == OrderSide.BUY else OrderDirection.ORDER_DIRECTION_SELL
            )

            # Place order
            if order_type == OrderType.MARKET:
                response = await client.orders.post_order(
                    figi=figi,
                    quantity=quantity,
                    direction=direction,
                    account_id=self._account_id,
                    order_type=tinkoff_order_type,
                )
            else:
                if price is None:
                    raise TinkoffClientError('Price required for limit orders')

                response = await client.orders.post_order(
                    figi=figi,
                    quantity=quantity,
                    price=decimal_to_quotation(price),
                    direction=direction,
                    account_id=self._account_id,
                    order_type=tinkoff_order_type,
                )

            return {
                'external_order_id': response.order_id,
                'figi': response.figi,
                'direction': response.direction,
                'initial_order_price': money_value_to_decimal(response.initial_order_price)
                if response.initial_order_price
                else None,
                'lots_requested': response.lots_requested,
                'lots_executed': response.lots_executed,
            }
        except Exception as e:
            raise TinkoffClientError(f'Failed to place order: {e}') from e

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel order via Tinkoff Invest API.

        Args:
            order_id: Tinkoff order identifier

        Returns:
            True if cancellation successful

        Raises:
            TinkoffClientError: If cancellation fails
        """
        client = self.__ensure_client()

        if not self._account_id:
            raise TinkoffClientError('Account ID not set')

        try:
            await client.orders.cancel_order(account_id=self._account_id, order_id=order_id)
            return True
        except Exception as e:
            raise TinkoffClientError(f'Failed to cancel order {order_id}: {e}') from e

    async def get_portfolio(self) -> dict[str, Any]:
        """
        Get portfolio positions.

        Returns:
            Portfolio with positions and balances

        Raises:
            TinkoffClientError: If portfolio fetch fails
        """
        client = self.__ensure_client()

        if not self._account_id:
            raise TinkoffClientError('Account ID not set')

        try:
            response = await client.operations.get_portfolio(account_id=self._account_id)

            positions = []
            for position in response.positions:
                positions.append(
                    {
                        'figi': position.figi,
                        'quantity': quotation_to_decimal(position.quantity),
                        'average_price': money_value_to_decimal(position.average_position_price)
                        if position.average_position_price
                        else Decimal('0'),
                        'current_price': money_value_to_decimal(position.current_price)
                        if position.current_price
                        else Decimal('0'),
                    },
                )

            total_value = money_value_to_decimal(response.total_amount_portfolio)

            return {
                'positions': positions,
                'total_value': total_value,
                'currency': response.total_amount_portfolio.currency if response.total_amount_portfolio else 'rub',
            }
        except Exception as e:
            raise TinkoffClientError(f'Failed to get portfolio: {e}') from e

    async def get_account_info(self) -> dict[str, Any]:
        """
        Get account information.

        Returns:
            Account details

        Raises:
            TinkoffClientError: If account info fetch fails
        """
        client = self.__ensure_client()

        try:
            accounts_response = await client.users.get_accounts()

            if not accounts_response.accounts:
                raise TinkoffClientError('No accounts found')

            account = None
            for acc in accounts_response.accounts:
                if acc.id == self._account_id:
                    account = acc
                    break

            if not account:
                raise TinkoffClientError(f'Account {self._account_id} not found')

            return {
                'account_id': account.id,
                'name': account.name,
                'type': str(account.type),
                'status': str(account.status),
                'access_level': str(account.access_level),
            }
        except Exception as e:
            raise TinkoffClientError(f'Failed to get account info: {e}') from e

    async def get_candles(
        self,
        figi: str,
        interval: CandleInterval,
        from_time: Any,
        to_time: Any,
    ) -> list[dict[str, Any]]:
        """
        Get historical candles for instrument.

        Args:
            figi: Financial Instrument Global Identifier
            interval: Candle interval
            from_time: Start time
            to_time: End time

        Returns:
            List of candles with OHLCV data

        Raises:
            TinkoffClientError: If candles fetch fails
        """
        client = self.__ensure_client()

        try:
            response = await client.market_data.get_candles(figi=figi, from_=from_time, to=to_time, interval=interval)

            candles = []
            for candle in response.candles:
                candles.append(
                    {
                        'time': candle.time,
                        'open': quotation_to_decimal(candle.open),
                        'high': quotation_to_decimal(candle.high),
                        'low': quotation_to_decimal(candle.low),
                        'close': quotation_to_decimal(candle.close),
                        'volume': candle.volume,
                    },
                )

            return candles
        except Exception as e:
            raise TinkoffClientError(f'Failed to get candles: {e}') from e

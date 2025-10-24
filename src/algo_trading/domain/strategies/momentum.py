"""Momentum Trading Strategy - Domain Layer.

Buys when price momentum is strong, sells when momentum weakens.
"""

from decimal import Decimal

from .base import (MarketDataPoint, SignalType, StrategySignal,
                   TradingStrategyBase)


class MomentumStrategy(TradingStrategyBase):
    """
    Momentum trading strategy implementation.

    Strategy Rules:
    - BUY: Price momentum > threshold (strong upward trend)
    - SELL: Price momentum < -threshold (strong downward trend)
    - HOLD: Otherwise
    """

    def _validate_parameters(self) -> None:
        """Validate required momentum parameters."""
        required = {"lookback_period", "momentum_threshold", "position_size_pct"}

        missing = required - set(self.parameters.keys())
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

        # Validate types and ranges
        lookback = self.parameters["lookback_period"]
        if not isinstance(lookback, int) or lookback < 1:
            raise ValueError("lookback_period must be positive integer")

        threshold = Decimal(str(self.parameters["momentum_threshold"]))
        if threshold <= 0 or threshold > 1:
            raise ValueError("momentum_threshold must be between 0 and 1")

        position_pct = Decimal(str(self.parameters["position_size_pct"]))
        if position_pct <= 0 or position_pct > 1:
            raise ValueError("position_size_pct must be between 0 and 1")

    def generate_signal(
        self,
        instrument: str,
        current_data: MarketDataPoint,
        historical_data: list[MarketDataPoint],
    ) -> StrategySignal:
        """
        Generate momentum-based trading signal.

        Args:
            instrument: Trading instrument
            current_data: Current market data
            historical_data: Historical prices

        Returns:
            StrategySignal (BUY/SELL/HOLD)
        """
        lookback_period = self.parameters["lookback_period"]
        momentum_threshold = Decimal(str(self.parameters["momentum_threshold"]))

        # Need enough historical data
        if len(historical_data) < lookback_period:
            return StrategySignal(
                signal_type=SignalType.HOLD,
                instrument=instrument,
                reason="Insufficient historical data",
            )

        # Calculate momentum: (current_price - past_price) / past_price
        current_price = current_data.price
        past_price = historical_data[-lookback_period].price

        if past_price == 0:
            return StrategySignal(
                signal_type=SignalType.HOLD,
                instrument=instrument,
                reason="Invalid past price (zero)",
            )

        momentum = (current_price - past_price) / past_price

        # Calculate confidence based on momentum strength
        confidence = min(abs(momentum) / momentum_threshold, Decimal("1.0"))

        # Generate signal
        if momentum > momentum_threshold:
            return StrategySignal(
                signal_type=SignalType.BUY,
                instrument=instrument,
                target_price=current_price,
                confidence=confidence,
                reason=f"Strong upward momentum: {momentum:.4f}",
            )
        elif momentum < -momentum_threshold:
            return StrategySignal(
                signal_type=SignalType.SELL,
                instrument=instrument,
                target_price=current_price,
                confidence=confidence,
                reason=f"Strong downward momentum: {momentum:.4f}",
            )
        else:
            return StrategySignal(
                signal_type=SignalType.HOLD,
                instrument=instrument,
                reason=f"Weak momentum: {momentum:.4f}",
            )

    def calculate_position_size(
        self,
        signal: StrategySignal,
        available_capital: Decimal,
        current_price: Decimal,
    ) -> Decimal:
        """
        Calculate position size based on available capital.

        Uses fixed percentage of capital and adjusts by signal confidence.

        Args:
            signal: Trading signal
            available_capital: Available capital
            current_price: Current price

        Returns:
            Position size (quantity)
        """
        position_size_pct = Decimal(str(self.parameters["position_size_pct"]))

        # Adjust position size by confidence
        confidence = signal.confidence or Decimal("1.0")
        adjusted_pct = position_size_pct * confidence

        # Calculate quantity
        capital_to_use = available_capital * adjusted_pct
        quantity = capital_to_use / current_price if current_price > 0 else Decimal("0")

        return quantity

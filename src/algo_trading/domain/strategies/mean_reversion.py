"""Mean Reversion Trading Strategy - Domain Layer.

Buys when price is below moving average, sells when above.
"""

from decimal import Decimal

from .base import (MarketDataPoint, SignalType, StrategySignal,
                   TradingStrategyBase)


class MeanReversionStrategy(TradingStrategyBase):
    """
    Mean reversion trading strategy implementation.

    Strategy Rules:
    - BUY: Price < (MA - threshold * StdDev) - oversold
    - SELL: Price > (MA + threshold * StdDev) - overbought
    - HOLD: Price within normal range
    """

    def _validate_parameters(self) -> None:
        """Validate required mean reversion parameters."""
        required = {"moving_average_period", "std_dev_threshold", "position_size_pct"}

        missing = required - set(self.parameters.keys())
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

        # Validate types and ranges
        ma_period = self.parameters["moving_average_period"]
        if not isinstance(ma_period, int) or ma_period < 2:
            raise ValueError("moving_average_period must be >= 2")

        std_threshold = Decimal(str(self.parameters["std_dev_threshold"]))
        if std_threshold <= 0:
            raise ValueError("std_dev_threshold must be positive")

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
        Generate mean reversion signal.

        Args:
            instrument: Trading instrument
            current_data: Current market data
            historical_data: Historical prices

        Returns:
            StrategySignal (BUY/SELL/HOLD)
        """
        ma_period = self.parameters["moving_average_period"]
        std_threshold = Decimal(str(self.parameters["std_dev_threshold"]))

        # Need enough data for MA calculation
        if len(historical_data) < ma_period:
            return StrategySignal(
                signal_type=SignalType.HOLD,
                instrument=instrument,
                reason="Insufficient historical data",
            )

        # Calculate moving average
        recent_prices = [d.price for d in historical_data[-ma_period:]]
        moving_average = Decimal(sum((p for p in recent_prices), Decimal("0"))) / Decimal(len(recent_prices))

        # Calculate standard deviation
        variance = (
                Decimal(sum(((p - moving_average) ** 2 for p in recent_prices), Decimal("0"))) /
                Decimal(len(recent_prices))
        )
        std_dev = Decimal(str(variance)) ** Decimal("0.5")

        # Calculate bands
        lower_band = moving_average - (Decimal(str(std_threshold)) * std_dev)
        upper_band = moving_average + (Decimal(str(std_threshold)) * std_dev)

        current_price = current_data.price

        # Calculate distance from MA in std devs
        if std_dev > 0:
            z_score = abs((current_price - moving_average) / std_dev)
            confidence = min(z_score / std_threshold, Decimal("1.0"))
        else:
            confidence = Decimal("0")

        # Generate signal
        if current_price < lower_band:
            # Oversold - buy signal
            return StrategySignal(
                signal_type=SignalType.BUY,
                instrument=instrument,
                target_price=current_price,
                confidence=confidence,
                reason=f"Oversold: price {current_price} < lower band {lower_band:.2f}",
            )
        elif current_price > upper_band:
            # Overbought - sell signal
            return StrategySignal(
                signal_type=SignalType.SELL,
                instrument=instrument,
                target_price=current_price,
                confidence=confidence,
                reason=f"Overbought: price {current_price} > upper band {upper_band:.2f}",
            )
        else:
            # Within normal range
            return StrategySignal(
                signal_type=SignalType.HOLD,
                instrument=instrument,
                reason=f"Price {current_price} within bands [{lower_band:.2f}, {upper_band:.2f}]",
            )

    def calculate_position_size(
        self,
        signal: StrategySignal,
        available_capital: Decimal,
        current_price: Decimal,
    ) -> Decimal:
        """
        Calculate position size based on available capital and signal strength.

        Args:
            signal: Trading signal
            available_capital: Available capital
            current_price: Current price

        Returns:
            Position size (quantity)
        """
        position_size_pct = Decimal(str(self.parameters["position_size_pct"]))

        # Adjust by confidence (stronger deviation = larger position)
        confidence = signal.confidence or Decimal("1.0")
        adjusted_pct = position_size_pct * confidence

        # Calculate quantity
        capital_to_use = available_capital * adjusted_pct
        quantity = capital_to_use / current_price if current_price > 0 else Decimal("0")

        return quantity

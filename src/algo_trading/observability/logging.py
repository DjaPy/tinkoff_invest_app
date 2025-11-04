"""Structured logging utilities for algorithmic trading.

Provides logging with context enrichment using standard Python logging.
"""

import json
import logging
from typing import Any


def configure_logging(log_level: str = 'INFO', json_logs: bool = True) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Enable JSON-formatted logs (default: True)
    """


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class TradingLogger:
    """
    Wrapper for trading-specific logging.

    Provides convenience methods for common trading events with JSON formatting.
    """

    def __init__(self, component: str) -> None:
        """
        Initialize trading logger.

        Args:
            component: Component name (e.g., 'strategy_manager', 'order_executor')
        """
        self.logger = get_logger(component)
        self.component = component

    def _log_json(self, level: str, event_type: str, **data: Any) -> None:
        """Log event as JSON."""
        log_data = {'event_type': event_type, 'component': self.component, **data}
        log_method = getattr(self.logger, level.lower())
        log_method(json.dumps(log_data))

    def log_strategy_event(
        self,
        event: str,
        strategy_id: str,
        strategy_name: str,
        **kwargs: Any,
    ) -> None:
        """
        Log a strategy lifecycle event.

        Args:
            event: Event type (created, started, paused, stopped, deleted)
            strategy_id: Strategy UUID
            strategy_name: Strategy name
            **kwargs: Additional context
        """
        self._log_json(
            'info',
            'strategy_event',
            event=event,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            **kwargs,
        )

    def log_order_event(
        self,
        event: str,
        order_id: str,
        strategy_id: str,
        instrument: str,
        side: str,
        quantity: float,
        **kwargs: Any,
    ) -> None:
        """
        Log an order lifecycle event.

        Args:
            event: Event type (placed, filled, cancelled, rejected)
            order_id: Order UUID
            strategy_id: Strategy UUID
            instrument: Trading instrument
            side: Order side (buy/sell)
            quantity: Order quantity
            **kwargs: Additional context
        """
        self._log_json(
            'info',
            'order_event',
            event=event,
            order_id=order_id,
            strategy_id=strategy_id,
            instrument=instrument,
            side=side,
            quantity=quantity,
            **kwargs,
        )

    def log_risk_event(
        self,
        event: str,
        strategy_id: str,
        rule: str,
        severity: str,
        current_value: float,
        limit_value: float,
        **kwargs: Any,
    ) -> None:
        """
        Log a risk management event.

        Args:
            event: Event type (violation, check_passed, check_failed)
            strategy_id: Strategy UUID
            rule: Risk rule violated
            severity: Violation severity
            current_value: Current metric value
            limit_value: Limit threshold
            **kwargs: Additional context
        """
        level = 'warning' if event == 'violation' else 'info'

        self._log_json(
            level,
            'risk_event',
            event=event,
            strategy_id=strategy_id,
            rule=rule,
            severity=severity,
            current_value=current_value,
            limit_value=limit_value,
            **kwargs,
        )

    def log_session_event(
        self,
        event: str,
        session_id: str,
        strategy_id: str,
        **kwargs: Any,
    ) -> None:
        """
        Log a trading session event.

        Args:
            event: Event type (started, ended, metrics_updated)
            session_id: Session UUID
            strategy_id: Strategy UUID
            **kwargs: Additional context
        """
        self._log_json(
            'info',
            'session_event',
            event=event,
            session_id=session_id,
            strategy_id=strategy_id,
            **kwargs,
        )

    def log_performance_event(
        self,
        strategy_id: str,
        pnl: float,
        return_pct: float,
        sharpe_ratio: float | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Log performance metrics.

        Args:
            strategy_id: Strategy UUID
            pnl: Profit and loss
            return_pct: Return percentage
            sharpe_ratio: Sharpe ratio (optional)
            **kwargs: Additional context
        """
        self._log_json(
            'info',
            'performance_metrics',
            strategy_id=strategy_id,
            pnl=pnl,
            return_pct=return_pct,
            sharpe_ratio=sharpe_ratio,
            **kwargs,
        )

    def log_error(
        self,
        error: str,
        error_type: str,
        **kwargs: Any,
    ) -> None:
        """
        Log an error event.

        Args:
            error: Error message
            error_type: Error classification
            **kwargs: Additional context
        """
        self._log_json(
            'error',
            'error_occurred',
            error=error,
            error_type=error_type,
            **kwargs,
        )

    def log_market_data_event(
        self,
        event: str,
        instrument: str,
        timeframe: str,
        **kwargs: Any,
    ) -> None:
        """
        Log market data events.

        Args:
            event: Event type (update_received, cache_hit, cache_miss)
            instrument: Trading instrument
            timeframe: Data timeframe
            **kwargs: Additional context
        """
        self._log_json(
            'debug',
            'market_data_event',
            event=event,
            instrument=instrument,
            timeframe=timeframe,
            **kwargs,
        )

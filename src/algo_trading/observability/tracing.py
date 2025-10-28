"""OpenTelemetry tracing for algorithmic trading.

Provides distributed tracing capabilities for trading operations.
"""

from functools import wraps
from typing import Any, Callable

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Initialize tracer provider
resource = Resource(attributes={SERVICE_NAME: 'algo-trading-app'})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Get tracer
tracer = trace.get_tracer('algo_trading')


def trace_operation(operation_name: str | None = None) -> Callable:
    """
    Decorator to trace an operation with OpenTelemetry.

    Args:
        operation_name: Name of the operation (defaults to function name)

    Returns:
        Decorated function with tracing
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            span_name = operation_name or func.__name__
            with tracer.start_as_current_span(span_name) as span:
                # Add function metadata
                span.set_attribute('function.name', func.__name__)
                span.set_attribute('function.module', func.__module__)

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute('success', True)
                    return result
                except Exception as e:
                    span.set_attribute('success', False)
                    span.set_attribute('error.type', type(e).__name__)
                    span.set_attribute('error.message', str(e))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


def add_span_attributes(**attributes: Any) -> None:
    """
    Add attributes to the current span.

    Args:
        **attributes: Key-value pairs to add to span
    """
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        for key, value in attributes.items():
            current_span.set_attribute(key, value)


def trace_strategy_operation(
    strategy_id: str,
    operation: str,
) -> Callable:
    """
    Decorator to trace strategy operations.

    Args:
        strategy_id: Strategy UUID
        operation: Operation name

    Returns:
        Decorated function with strategy tracing
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(f'strategy.{operation}') as span:
                span.set_attribute('strategy.id', strategy_id)
                span.set_attribute('strategy.operation', operation)

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute('success', True)
                    return result
                except Exception as e:
                    span.set_attribute('success', False)
                    span.set_attribute('error.type', type(e).__name__)
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


def trace_order_operation(
    order_id: str,
    instrument: str,
    side: str,
) -> Callable:
    """
    Decorator to trace order operations.

    Args:
        order_id: Order UUID
        instrument: Trading instrument
        side: Order side (buy/sell)

    Returns:
        Decorated function with order tracing
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span('order.execute') as span:
                span.set_attribute('order.id', order_id)
                span.set_attribute('order.instrument', instrument)
                span.set_attribute('order.side', side)

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute('order.status', 'success')
                    return result
                except Exception as e:
                    span.set_attribute('order.status', 'failed')
                    span.set_attribute('error.type', type(e).__name__)
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator

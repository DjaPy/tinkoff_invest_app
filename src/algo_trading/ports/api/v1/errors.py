"""
RFC7807 Error Handling for Algorithmic Trading API.

Provides standardized error responses following RFC7807 Problem Details spec.
"""

from http import HTTPStatus
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ProblemDetail(BaseModel):
    """RFC7807 Problem Details for HTTP APIs."""

    type: str = Field(description="URI reference identifying the problem type")
    title: str = Field(description="Short, human-readable summary")
    status: int = Field(description="HTTP status code")
    detail: str | None = Field(None, description="Human-readable explanation")
    instance: str | None = Field(None, description="URI reference to specific occurrence")
    invalid_params: list[dict[str, Any]] | None = Field(None, description="Validation errors")


class TradingAPIException(HTTPException):
    """Base exception for trading API errors."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        type_uri: str | None = None,
        invalid_params: list[dict[str, Any]] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.type_uri = type_uri or f"https://api.trading.com/errors/{status_code}"
        self.invalid_params = invalid_params


class StrategyNotFoundException(TradingAPIException):
    """Strategy not found error."""

    def __init__(self, strategy_id: str):
        super().__init__(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Strategy with ID {strategy_id} not found",
            type_uri="https://api.trading.com/errors/strategy-not-found",
        )


class StrategyValidationException(TradingAPIException):
    """Strategy validation error."""

    def __init__(self, detail: str, invalid_params: list[dict[str, Any]] | None = None):
        super().__init__(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=detail,
            type_uri="https://api.trading.com/errors/strategy-validation",
            invalid_params=invalid_params,
        )


class InvalidStateTransitionException(TradingAPIException):
    """Invalid strategy state transition."""

    def __init__(self, current_status: str, new_status: str):
        super().__init__(
            status_code=HTTPStatus.CONFLICT,
            detail=f"Cannot transition from {current_status} to {new_status}",
            type_uri="https://api.trading.com/errors/invalid-state-transition",
        )


class OrderNotFoundException(TradingAPIException):
    """Order not found error."""

    def __init__(self, order_id: str):
        super().__init__(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
            type_uri="https://api.trading.com/errors/order-not-found",
        )


class OrderValidationException(TradingAPIException):
    """Order validation error."""

    def __init__(self, detail: str, invalid_params: list[dict[str, Any]] | None = None):
        super().__init__(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=detail,
            type_uri="https://api.trading.com/errors/order-validation",
            invalid_params=invalid_params,
        )


class RiskLimitExceededException(TradingAPIException):
    """Risk limit exceeded error."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=HTTPStatus.FORBIDDEN,
            detail=detail,
            type_uri="https://api.trading.com/errors/risk-limit-exceeded",
        )


class PositionNotFoundException(TradingAPIException):
    """Position not found error."""

    def __init__(self, position_id: str):
        super().__init__(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Position with ID {position_id} not found",
            type_uri="https://api.trading.com/errors/position-not-found",
        )


class InsufficientDataException(TradingAPIException):
    """Insufficient market data error."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=detail,
            type_uri="https://api.trading.com/errors/insufficient-data",
        )


async def trading_api_exception_handler(
    request: Request, exc: TradingAPIException
) -> JSONResponse:
    """Handle TradingAPIException and return RFC7807 response."""
    problem = ProblemDetail(
        type=exc.type_uri,
        title=HTTPStatus(exc.status_code).phrase,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url),
        invalid_params=exc.invalid_params,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle generic HTTPException and return RFC7807 response."""
    problem = ProblemDetail(
        type=f"https://api.trading.com/errors/{exc.status_code}",
        title=HTTPStatus(exc.status_code).phrase,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic ValidationError and return RFC7807 response."""
    from pydantic import ValidationError

    if not isinstance(exc, ValidationError):
        raise exc

    invalid_params = [
        {"name": ".".join(str(loc) for loc in err["loc"]), "reason": err["msg"]}
        for err in exc.errors()
    ]

    problem = ProblemDetail(
        type="https://api.trading.com/errors/validation-error",
        title="Validation Error",
        status=HTTPStatus.UNPROCESSABLE_ENTITY,
        detail="Request validation failed",
        instance=str(request.url),
        invalid_params=invalid_params,
    )

    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content=problem.model_dump(exclude_none=True),
    )

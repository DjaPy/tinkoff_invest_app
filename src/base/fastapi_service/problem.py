# pylint: disable=no-name-in-module

import typing
from http import HTTPStatus
from typing import Any, Optional

from fastapi import Response, status
from pydantic import BaseModel, ConfigDict, model_validator
from starlette.background import BackgroundTask

__all__ = ['Problem', 'ProblemResponse', 'ValidationError', 'Unauthorized', 'Forbidden', 'NotFound',
           'UnprocessableEntity', 'InternalServerError']

from typing_extensions import Annotated, TypedDict


class Problem(BaseModel):
    type: Optional[str] = None
    title: Optional[str] = None
    status: Optional[HTTPStatus] = None
    detail: Optional[Any] = None
    instance: Optional[str] = None
    invalid_params: Annotated[Any | None, 'invalid-params'] = None

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode='before')
    def title_without_type(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
        type_ = values.get('type')
        title = values.get('title')
        status = values.get('status')
        if not type_ and status:
            values['title'] = title or HTTPStatus(status).phrase

        return values


class ValidationError(Problem):
    class Param(TypedDict):
        name: str
        reason: str

    type: typing.Literal['validation-error'] = 'validation-error'
    title: typing.Literal["Your request parameters didn't validate."] = "Your request parameters didn't validate."
    status: typing.Literal[HTTPStatus.BAD_REQUEST] = HTTPStatus.BAD_REQUEST
    invalid_params: list[Param]


class Unauthorized(Problem):
    type: typing.Literal['unauthorized'] = 'unauthorized'
    title: typing.Literal[
        'The request has not been applied because it lacks valid authentication credentials for the target resource.'
    ] = 'The request has not been applied because it lacks valid authentication credentials for the target resource.'
    status: typing.Literal[HTTPStatus.UNAUTHORIZED] = HTTPStatus.UNAUTHORIZED


class Forbidden(Problem):
    type: typing.Literal['forbidden'] = 'forbidden'
    title: typing.Literal[
        'The server understood the request but refuses to authorize it.'
    ] = 'The server understood the request but refuses to authorize it.'
    status: typing.Literal[HTTPStatus.FORBIDDEN] = HTTPStatus.FORBIDDEN


class NotFound(Problem):
    type: typing.Literal['not-found'] = 'not-found'
    title: typing.Literal['Requested resource is not available.'] = 'Requested resource is not available.'
    status: typing.Literal[HTTPStatus.NOT_FOUND] = HTTPStatus.NOT_FOUND


class UnprocessableEntity(Problem):
    type: str
    status: typing.Literal[HTTPStatus.UNPROCESSABLE_ENTITY] = HTTPStatus.UNPROCESSABLE_ENTITY


class InternalServerError(Problem):
    type: typing.Literal['internal-server-error'] = 'internal-server-error'
    title: typing.Literal['Internal server error.'] = 'Internal server error.'
    status: typing.Literal[HTTPStatus.INTERNAL_SERVER_ERROR] = HTTPStatus.INTERNAL_SERVER_ERROR


class ProblemResponse(Response):
    media_type = 'application/problem+json'

    def __init__(  # pylint: disable=too-many-arguments
            self,
            content: Problem,
            status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers: typing.Optional[dict] = None,
            media_type: typing.Optional[str] = None,
            background: typing.Optional[BackgroundTask] = None,
    ) -> None:
        if isinstance(content, Problem):
            status_code = content.status.value if content.status else status_code

        super().__init__(content, status_code, headers, media_type, background)

    def render(self, content: Any) -> bytes:
        if not isinstance(content, Problem):
            raise TypeError('the content must be Problem')

        return content.model_dump_json(exclude_none=True, by_alias=True).encode('utf-8')

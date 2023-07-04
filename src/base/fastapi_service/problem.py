# pylint: disable=no-name-in-module

import typing
from http import HTTPStatus
from typing import Any, Optional, TypedDict

from fastapi import Response, status
from pydantic import BaseModel, Field, root_validator
from starlette.background import BackgroundTask

__all__ = ['Problem', 'ProblemResponse', 'ValidationError', 'Unauthorized', 'Forbidden', 'NotFound',
           'UnprocessableEntity', 'InternalServerError']


class Problem(BaseModel):
    type: Optional[str] = None
    title: Optional[str] = None
    status: Optional[HTTPStatus] = None
    detail: Optional[Any] = None
    instance: Optional[str] = None
    invalid_params: Optional[Any] = None

    class Config:
        fields = {'invalid_params': 'invalid-params'}
        allow_population_by_field_name = True

    @root_validator
    def title_without_type(cls, values: dict[str, Any]) -> dict[str, Any]:  # pylint: disable=no-self-argument
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

    type: str = Field('validation-error', const=True)
    title: str = Field("Your request parameters didn't validate.", const=True)
    status: HTTPStatus = Field(HTTPStatus.BAD_REQUEST, const=True)
    invalid_params: list[Param]


class Unauthorized(Problem):
    type: str = Field('unauthorized', const=True)
    title: str = Field(
        'The request has not been applied because it lacks valid authentication credentials for the target resource.',
        const=True)
    status: HTTPStatus = Field(HTTPStatus.UNAUTHORIZED, const=True)


class Forbidden(Problem):
    type: str = Field('forbidden', const=True)
    title: str = Field('The server understood the request but refuses to authorize it.', const=True)
    status: HTTPStatus = Field(HTTPStatus.FORBIDDEN, const=True)


class NotFound(Problem):
    type: str = Field('not-found', const=True)
    title: str = Field('Requested resource is not available.', const=True)
    status: HTTPStatus = Field(HTTPStatus.NOT_FOUND, const=True)


class UnprocessableEntity(Problem):
    type: str
    status: HTTPStatus = Field(HTTPStatus.UNPROCESSABLE_ENTITY, const=True)


class InternalServerError(Problem):
    type: str = Field('internal-server-error', const=True)
    title: str = Field('Internal server error.', const=True)
    status: HTTPStatus = Field(HTTPStatus.INTERNAL_SERVER_ERROR, const=True)


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

        return content.json(exclude_none=True, by_alias=True).encode('utf-8')

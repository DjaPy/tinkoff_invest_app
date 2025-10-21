# pylint: disable=no-name-in-module

from http import HTTPStatus
from typing import Any

from fastapi import Response, status
from pydantic import BaseModel, Field, model_validator
from starlette.background import BackgroundTask

__all__ = [
    'Problem',
    'ProblemResponse',
    'ValidationError',
    'Unauthorized',
    'Forbidden',
    'NotFound',
    'UnprocessableEntity',
    'InternalServerError',
]

from typing_extensions import TypedDict


class Problem(BaseModel):
    type: str | None = None
    title: str | None = None
    status: HTTPStatus | None = None
    detail: Any | None = None
    instance: str | None = None
    invalid_params: Any | None = None

    class Config:
        populate_by_name = True

    @model_validator(mode='before')
    @classmethod
    def title_without_type(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values:
            type_ = values.get('type')
            title = values.get('title')
            status_ = values.get('status')
            if not type_ and status_:
                values['title'] = title or HTTPStatus(status_).phrase
        return values


class ValidationError(Problem):
    class Param(TypedDict):
        name: str
        reason: str

    type: str = Field('validation-error')
    title: str = Field('Your request parameters didn`t validate.')
    status: HTTPStatus = Field(HTTPStatus.BAD_REQUEST)
    invalid_params: list[Param]


class Unauthorized(Problem):
    type: str = Field('unauthorized')
    title: str = Field(
        'The request has not been applied because it lacks valid authentication credentials for the target resource.',
    )
    status: HTTPStatus = Field(HTTPStatus.UNAUTHORIZED)


class Forbidden(Problem):
    type: str = Field('forbidden')
    title: str = Field(
        'The server understood the request but refuses to authorize it.'
    )
    status: HTTPStatus = Field(HTTPStatus.FORBIDDEN)


class NotFound(Problem):
    type: str = Field('not-found')
    title: str = Field('Requested resource is not available.')
    status: HTTPStatus = Field(HTTPStatus.NOT_FOUND)


class UnprocessableEntity(Problem):
    type: str
    status: HTTPStatus = Field(HTTPStatus.UNPROCESSABLE_ENTITY)


class InternalServerError(Problem):
    type: str = Field('internal-server-error')
    title: str = Field('Internal server error.')
    status: HTTPStatus = Field(HTTPStatus.INTERNAL_SERVER_ERROR)


class ProblemResponse(Response):
    media_type = 'application/problem+json'

    def __init__(
        self,
        content: Problem,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers: dict | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        if isinstance(content, Problem):
            status_code = content.status.value if content.status else status_code

        super().__init__(content, status_code, headers, media_type, background)

    def render(self, content: Any) -> bytes:
        if not isinstance(content, Problem):
            raise TypeError('the content must be Problem')

        return content.json(exclude_none=True, by_alias=True).encode('utf-8')

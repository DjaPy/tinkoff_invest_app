import typing
from http import HTTPStatus
from typing import Any

from fastapi import Response, status
from pydantic import BaseModel, ConfigDict, model_validator
from starlette.background import BackgroundTask

__all__ = [
    'Conflict',
    'Forbidden',
    'InternalServerError',
    'NotFound',
    'Problem',
    'ProblemResponse',
    'Unauthorized',
    'UnprocessableEntity',
    'ValidationErrorSchema',
]

from typing_extensions import Annotated, TypedDict


class Problem(BaseModel):
    type: str | None = None
    title: str | None = None
    status: HTTPStatus | None = None
    detail: Any | None = None
    instance: str | None = None
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


class ValidationErrorSchema(Problem):
    class Param(TypedDict):
        name: str
        reason: str

    type: str = 'validation-error'
    title: str = "Your request parameters didn't validate."
    status: HTTPStatus = HTTPStatus.BAD_REQUEST
    invalid_params: list[Param]


class Unauthorized(Problem):
    type: str = 'unauthorized'
    title: str = ('The request has not been applied because it lacks valid '
                  'authentication credentials for the target resource.')
    status: HTTPStatus = HTTPStatus.UNAUTHORIZED


class Forbidden(Problem):
    type: str = 'forbidden'
    title: str = 'The server understood the request but refuses to authorize it.'
    status: HTTPStatus = HTTPStatus.FORBIDDEN


class Conflict(Problem):
    type: str = 'conflict'
    title: str = 'The request could not be completed due to a conflict with the current state of the target resource.'
    status: HTTPStatus = HTTPStatus.CONFLICT


class NotFound(Problem):
    type: str = 'not-found'
    title: str = 'Requested resource is not available.'
    status: HTTPStatus = HTTPStatus.NOT_FOUND


class UnprocessableEntity(Problem):
    type: str
    status: HTTPStatus = HTTPStatus.UNPROCESSABLE_ENTITY


class InternalServerError(Problem):
    type: str = 'internal-server-error'
    title: str = 'Internal server error.'
    status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR


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

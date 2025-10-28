from typing import Callable

from fastapi.routing import APIRoute
from opentelemetry import trace
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

tracer = trace.get_tracer(__name__)


class OpenTelemetryRoute(APIRoute):
    BODY_LENGTH_TRACE = 1024

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def wrap_handler_with_span(request: Request) -> Response:
            with tracer.start_as_current_span('fastapi server') as span:
                body = await request.body()
                if body:
                    span.set_attribute('request.payload', body[:self.BODY_LENGTH_TRACE])
                try:
                    response: Response = await original_route_handler(request)
                    if (b'content-type', b'image/jpeg') in response.raw_headers:
                        return response
                    span.set_attribute('response.payload', response.body[:self.BODY_LENGTH_TRACE])
                    return response
                except HTTPException as error:
                    span.add_event('Exception', attributes={'Exception': str(error.detail)})
                    raise HTTPException(status_code=error.status_code, detail=error.detail) from error

        return wrap_handler_with_span

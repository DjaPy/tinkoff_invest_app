import asyncio
import io
import time
import traceback
from functools import partial
from http import HTTPStatus
from typing import Any, Awaitable, Callable, Coroutine, Optional, Type

import yaml
from aiomisc import Service
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute, APIRouter
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import Counter, Gauge, Histogram
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.routing import Match
from uvicorn.config import Config

from . import FastAPISettings
from .problem import Problem, ProblemResponse
from .uvicorn_server import Server
from ..consts import FASTAPI

ExceptionHandlerType = Callable[[Request, Any], Coroutine[Any, Any, Response]]
ExceptionHandlerMethodType = Callable[['FastAPIService', Request, Any], Coroutine[Any, Any, Response]]


class FastAPIService(Service):
    openapi_yaml_url = '/openapi.yaml'

    HTTP_PANIC_RECOVERY_TOTAL = Counter(
        'http_panic_recovery_total',
        'Total number of recovered panics.',
        ['http_service', 'http_method', 'http_handler'],
    )
    HTTP_REQUEST_DURATION_SECONDS = Histogram(
        'http_request_duration_seconds',
        'The latency of the HTTP requests.',
        ['http_service', 'http_handler', 'http_method', 'http_code'],
        buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10],
    )
    HTTP_REQUESTS_INFLIGHT = Gauge(
        'http_requests_inflight',
        'The number of inflight requests being handled at the same time.',
        ['http_service', 'http_handler'],
    )
    HTTP_RESPONSE_SIZE_BYTES = Histogram(
        'http_response_size_bytes',
        'The size of the HTTP responses.',
        ['http_service', 'http_handler', 'http_method', 'http_code'],
        buckets=[100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000, 100_000_000, 1_000_000_000],
    )

    # RFC7807 Problem Details for HTTP APIs https://datatracker.ietf.org/doc/html/rfc7807
    async def debug_exception_handler_by_default(self, request: Request, exc: Any) -> ProblemResponse:
        status_ = HTTPStatus.INTERNAL_SERVER_ERROR
        detail = traceback.format_exception(exc, value=exc, tb=exc.__traceback__)
        problem = Problem(title=status_.phrase, status=status_, detail=detail, instance=request.url.path)
        return ProblemResponse(content=problem)

    async def http_exception_handler_by_default(self, request: Request, exc: HTTPException) -> ProblemResponse:
        status_ = HTTPStatus(exc.status_code)
        detail = exc.detail if exc.detail != status_.phrase else None
        problem = Problem(title=status_.phrase, status=status_, detail=detail, instance=request.url.path)
        self.HTTP_PANIC_RECOVERY_TOTAL.labels(self._app_name, request.url.path, request.method).inc()
        return ProblemResponse(content=problem)

    async def validation_exception_handler_by_default(
            self,
            request: Request,
            exc: RequestValidationError,
    ) -> ProblemResponse:
        status_ = HTTPStatus.BAD_REQUEST
        problem = Problem(title=status_.phrase, status=status_, instance=request.url.path,
                          invalid_params=exc.errors())
        return ProblemResponse(content=problem)

    MAP_EXCEPTION_HANDLER: dict[Type[Exception], ExceptionHandlerType | ExceptionHandlerMethodType] = {
        Exception: debug_exception_handler_by_default,
        StarletteHTTPException: http_exception_handler_by_default,
        RequestValidationError: validation_exception_handler_by_default,
    }

    def __init__(
            self,
            settings: FastAPISettings,
            routers: list[APIRouter],
            context_name: str = FASTAPI,
            app_name: str = '',
            version: str = '0.0.1',
    ) -> None:
        super().__init__()
        self._settings = settings
        self._app_name = app_name
        self._context_name = context_name
        self._version = version
        self.__fastapi = FastAPI(title=self._app_name, version=self._version)
        self.__task: Awaitable[Any] | None = None
        self.__server_main: Server | None = None

        self._add_routers(routers)
        if self._settings.openapi_yaml_url:
            self._add_openapi_yaml(self._settings.openapi_yaml_url)

    def _add_routers(self, routers: list[APIRouter]) -> None:
        self._routers = routers
        for router in self._routers:
            self.__fastapi.include_router(router)

    def _add_openapi_yaml(self, path: str) -> None:
        self.__fastapi.add_route(path, self.openapi_yaml, include_in_schema=False)

    async def openapi_yaml(self, req: Request) -> Response:
        urls = (server_data.get("url") for server_data in self.__fastapi.servers)
        server_urls = {url for url in urls if url}
        root_path = req.scope.get("root_path", "").rstrip("/")
        if root_path and root_path not in server_urls and self.root_path_in_servers:
            self.servers.insert(0, {"url": root_path})
            server_urls.add(root_path)
        openapi = self.__fastapi.openapi()
        openapi_yaml = io.StringIO()
        yaml.dump(openapi, openapi_yaml, sort_keys=False, allow_unicode=True)
        return Response(openapi_yaml.getvalue(), media_type='text/yaml')

    def map_exception_to_handler(
            self, exception: Type[Exception], handler: ExceptionHandlerType,
    ) -> None:
        self.MAP_EXCEPTION_HANDLER[exception] = handler

    async def start(self) -> None:
        self.context[self._context_name] = self.__fastapi

        for exception, handler in self.MAP_EXCEPTION_HANDLER.items():
            if hasattr(self, handler.__name__):
                self.__fastapi.exception_handler(exception)(partial(handler, self))
            else:
                self.__fastapi.exception_handler(exception)(handler)

        @self.__fastapi.middleware('http')
        async def prom_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
            start_time = time.time()

            http_handler = ''
            routes = next(filter(lambda x: isinstance(x, APIRoute) and x.matches(request.scope)[0] == Match.FULL,
                                 request.app.routes), None)
            if routes:
                http_handler = routes.path

            self.HTTP_REQUESTS_INFLIGHT.labels(self._app_name, http_handler).inc()

            response: Response = await call_next(request)

            resp_time = time.time() - start_time
            self.HTTP_REQUEST_DURATION_SECONDS.labels(
                self._app_name, http_handler, request.method, response.status_code,
            ).observe(resp_time)
            self.HTTP_RESPONSE_SIZE_BYTES.labels(
                self._app_name, http_handler, request.method, response.status_code,
            ).observe(int(response.headers.get('content-length', 0)))
            self.HTTP_REQUESTS_INFLIGHT.labels(self._app_name, http_handler).dec()

            return response

        FastAPIInstrumentor.instrument_app(self.__fastapi, tracer_provider=trace.get_tracer_provider())

        # https://github.com/encode/uvicorn/issues/541
        # https://stackoverflow.com/questions/23313720/asyncio-how-can-coroutines-be-used-in-signal-handlers
        # https://stackoverflow.com/questions/44850701/multiple-aiohttp-applications-running-in-the-same-process

        self.__server_main = Server(Config(  # pylint: disable=unexpected-keyword-arg
            app=self.__fastapi,
            host=self._settings.host,
            port=self._settings.port,
            workers=self._settings.uvicorn_workers,
            log_config=None,
        ))
        self.__task = asyncio.create_task(self.__server_main.serve())

    async def stop(self, exception: Optional[Exception] = None) -> None:
        if self.__server_main:
            self.__server_main.set_should_exit()
            await self.__task  # type: ignore

    @property
    def fastapi(self) -> FastAPI:
        return self.__fastapi

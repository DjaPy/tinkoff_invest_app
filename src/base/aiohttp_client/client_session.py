import asyncio
from types import SimpleNamespace
from typing import Any, Iterable, Type

import aiohttp
from aiohttp import hdrs

from aiohttp.http import SERVER_SOFTWARE
from prometheus_client import Counter, Histogram


class TraceConfigWithHeaderUserAgent(aiohttp.TraceConfig):
    labelnames = ['http_client_method']
    HTTP_CLIENT_STARTED_TOTAL = Counter(
        'http_client_started_total', 'Total number of HTTPs started on the client.', labelnames)
    HTTP_CLIENT_ERRORS_TOTAL = Counter(
        'http_client_errors_total', 'Total number of errors on the client.', labelnames)
    labelnames = ['http_client_method', 'http_client_status']
    HTTP_CLIENT_HANDLED_TOTAL = Counter(
        'http_client_handled_total', 'Total number of HTTPs completed by the client, regardless of success or failure.',
        labelnames)
    HTTP_CLIENT_HANDLING_SECONDS = Histogram(
        'http_client_handling_seconds',
        'Histogram of response latency (seconds) of the HTTP until it is finished by the application.',
        labelnames, buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10])

    async def on_request_start_trace(self, session: Any, trace_config_ctx: Any, params: Any) -> None:
        trace_config_ctx.start = asyncio.get_event_loop().time()
        self.HTTP_CLIENT_STARTED_TOTAL.labels(params.method).inc()
        params.headers[hdrs.USER_AGENT] = self._user_agent

    async def on_request_end_trace(self, session: Any, trace_config_ctx: Any, params: Any) -> None:
        elapsed = asyncio.get_event_loop().time() - trace_config_ctx.start
        self.HTTP_CLIENT_HANDLING_SECONDS.labels(params.method, params.response.status).observe(elapsed)
        self.HTTP_CLIENT_HANDLED_TOTAL.labels(params.method, params.response.status).inc()

    async def on_request_exception_trace(self, session: Any, trace_config_ctx: Any, params: Any) -> None:
        self.HTTP_CLIENT_ERRORS_TOTAL.labels(params.method).inc()

    def __init__(
            self,
            user_agent: str = SERVER_SOFTWARE,
            trace_config_ctx_factory: Type[SimpleNamespace] = SimpleNamespace,
    ):
        super().__init__(trace_config_ctx_factory)
        self._user_agent = user_agent
        self.on_request_start.append(self.on_request_start_trace)
        self.on_request_end.append(self.on_request_end_trace)
        self.on_request_exception.append(self.on_request_exception_trace)


class ClientRequest(aiohttp.ClientRequest):
    _user_agent: str = SERVER_SOFTWARE

    def update_auto_headers(self, skip_auto_headers: Iterable[str]) -> None:
        super().update_auto_headers(skip_auto_headers)

        self.headers[hdrs.USER_AGENT] = self._user_agent

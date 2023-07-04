import asyncio
import socket
from http import HTTPStatus
from os.path import join
from ssl import SSLContext
from typing import Any, Generic, Optional, Type, TypeVar

from aiohttp import ClientResponse, ClientTimeout, Fingerprint, MultipartWriter, ClientSession
from aiohttp.typedefs import StrOrURL
from aiomisc import Service
from pydantic import BaseModel
from yarl import URL

from src.base.aiohttp_client.config import ClientSettings

ResponseModel = TypeVar('ResponseModel', bound=BaseModel)
ErrorException = TypeVar('ErrorException', bound=Exception)
ClientSettingsType = TypeVar('ClientSettingsType', bound=ClientSettings)


class BaseClient(Generic[ClientSettingsType, ErrorException]):
    cfg: ClientSettingsType
    _exception: Type[ErrorException]
    client_name: str = 'base_client'

    def __init__(
        self,
        settings: ClientSettingsType,
        error_exception: Type[ErrorException],
        app_name: str = '',
        user_agent: str | None = None,
        client_name: str | None = None,
    ) -> None:
        self.cfg = settings
        self._exception = error_exception
        self.url = URL(self.cfg.url)
        self._user_agent = user_agent or f'{app_name}/{socket.gethostname()}/{self.__class__.__name__}'
        self._session = ClientSession(timeout=ClientTimeout(total=self.cfg.timeout))
        self.client_name = client_name or self.client_name
        ClientManagerService.set_client(self.client_name, self)

    async def _request(self, method: str, url: StrOrURL, **kwargs: Any) -> ClientResponse:
        return await self._session.request(method, url, **kwargs)

    async def _send_request(
        self,
        response_schema: Type[ResponseModel],
        path: Optional[str] = None,
        url: Optional[URL] = None,
        method: str = 'GET',
        ssl: Optional[SSLContext | bool | Fingerprint] = False,
        headers: Optional[dict[str, str]] = None,
        data: Optional[dict[str, Any] | MultipartWriter] = None,
        json: Optional[str | bytes] = None,
        **kwargs: Optional[Any]
    ) -> ResponseModel:
        url = url or self.url.with_path(join(self.url.path, path or ''))
        try:
            response: ClientResponse = await self._request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json,
                ssl=ssl,
                **kwargs,
            )
        except asyncio.TimeoutError as error:
            raise self._exception({'errors': 'Service unavailable'}) from error

        if response.status in (HTTPStatus.OK.real, HTTPStatus.CREATED.real, HTTPStatus.BAD_REQUEST.real):
            return response_schema.parse_raw(await response.read())

        raise self._exception(
            f'Error in request "{response.status}" method="{method}", url="{url}", body = {await response.text()}'
        )


class ClientManagerService(Service):
    _map_clients: dict[str, BaseClient] = {}

    def __init__(
        self,
        context_name: str = 'client_manager'
    ) -> None:
        super().__init__()
        self.context_name = context_name

    def __getitem__(self, item: str) -> BaseClient:
        return self._map_clients[item]

    @classmethod
    def set_client(cls, item: str, client: BaseClient) -> None:
        cls._map_clients[item] = client

    async def start(self) -> Any:
        self.context[self.context_name] = self

    async def stop(self, exception: Optional[Exception] = None) -> Any:
        pass

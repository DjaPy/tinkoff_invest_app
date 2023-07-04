class IMDBApiException(RuntimeError):
    ...


class ClientIMDBApi(BaseClient[IMDBClientSettings, IMDBApiException]):
    client_name = 'tinkoff_invest'

    async def get_(self, page: int = 1) -> list[dict]:
        ...

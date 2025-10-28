from pydantic import BaseModel, Field


class FastAPISettings(BaseModel):
    port: int = Field(8080, description='Строка подключения к базе данных')
    host: str = Field('0.0.0.0', description='ip на котором мы открываем порт')  # noqa: S104
    uvicorn_workers: int = Field(1, description='Количество воркеров uvicorn')
    debug: bool = Field(False, description='debug для FastAPI')
    openapi_yaml_url: str | None = Field(
        None,
        description='Путь по которому будет возвращаться openapi в yaml',
        examples=['/openapi.yaml'],
    )

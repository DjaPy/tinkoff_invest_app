from pydantic import BaseModel, Field


class FastAPISettings(BaseModel):
    port: int = Field(8080, description='Строка подключения к базе данных')
    host: str = Field('0.0.0.0', description='ip на котором мы открываем порт')  # nosec
    uvicorn_workers: int = Field(1, description='Количество воркеров uvicorn')
    debug: bool = Field(False, description='debug для FastAPI')

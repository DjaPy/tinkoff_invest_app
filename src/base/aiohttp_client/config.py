from pydantic import BaseModel, Field


class ClientSettings(BaseModel):
    url: str = Field(description='Базовая строка подключения к стороннему сервису')
    timeout: float = Field(10.0, description="Время ожидания ответа сервера")

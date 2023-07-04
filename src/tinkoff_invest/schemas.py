from typing import Any

from pydantic import BaseModel, Field


class EntityType(BaseModel):
    metadata: dict[str, Any] = Field(description='Метаданные типа данных')
    columns: list[str] = Field(description='Список колонок')
    data: list[Any] = Field(description='Список данных')


class CommonData(BaseModel):
    name: str = Field(description='Название типа данных')
    entity: EntityType = Field(description='Тип данных')

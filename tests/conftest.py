import logging
import uuid
from contextlib import contextmanager
from functools import partial
from typing import Any, Callable, TypeVar

import pytest
import rstr
from aiohttp import request
from beanie import init_beanie
from faker import Faker
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from src.algo_trading.adapters.models import BEANIE_MODELS
from src.config import config as build_config

pytest_plugins = [
    'fixtures_db_data',
]

logger = logging.getLogger(__name__)


@pytest.fixture
def fake():
    """Faker."""
    return Faker('ru-RU')


@pytest.fixture(scope='session')
def config():
    return build_config


@pytest.fixture
async def mongo_connection(config):
    name_database = f'{uuid.uuid4().hex}_pytest'
    _client = AsyncIOMotorClient(str(config.mongo_db.dsn))
    await init_beanie(database=_client[name_database], document_models=BEANIE_MODELS)
    logger.info(f'Connected to MongoDB, db={name_database}')
    yield _client
    await _client.drop_database(name_database)
    _client.close()


@pytest.fixture
async def get_session(mongo_connection):
    async with await mongo_connection.start_session() as session:
        yield session


ModelType = TypeVar('ModelType', bound=BaseModel)


class ModelGenerator:
    """Генерация данных по модели пидантика."""

    def __init__(self, fake: Faker) -> None:

        self.fake = fake

        self.map: dict[str, Callable] = {
            'integer': lambda *args: self.fake.pyint(),
            'number': lambda *args: self.fake.pydecimal(
                left_digits=5,
                right_digits=2,
                positive=True,
            ),
            'string': lambda *args: self.fake.pystr(),
            'date': lambda *args: self.fake.date_time().date(),
            'date-time': lambda *args: self.fake.date_time(),
            'uuid': lambda *args: uuid.uuid4(),
            'boolean': lambda *args: self.fake.pybool(),
            'array': lambda data: [self.value(data['items']) for _ in range(
                self.fake.random.randrange(1, 5),
            )],
            '$ref': lambda data: self.parse(self.models[data['$ref']]),
            'enum': lambda enum_values: self.fake.random.choice(enum_values),  # pylint: disable=unnecessary-lambda
            'object': lambda data: {self.fake.pystr(): self.value(
                data.get('additionalProperties', {}),
            )},
            'pattern': lambda data: rstr.xeger(data['pattern']),
            'any': lambda *args: self.fake.pystr(),
        }

        self.models: dict[str, Any] = {}
        self.override: dict[str, Any] = {}
        self.include_optional: bool = True

    def value(self, data: dict[str, Any]) -> Any:
        """Поучение случайного значения."""
        if 'allOf' in data:
            data = data['allOf'][0]
        if 'anyOf' in data:
            data = data['anyOf'][0]
        try:
            if 'pattern' in data:
                return self.map['pattern'](data)
            return self.map[data.get('format') or data.get('type', '$ref')](data)
        except KeyError:
            return self.map['any']()

    def parse(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Распарсивание данных."""
        res = {}
        if 'enum' in schema:
            return self.map['enum'](schema['enum'])
        if 'const' in schema:
            return schema['const']
        for field, data in schema['properties'].items():
            if field not in schema.get('required', []) and self.include_optional is True and self.fake.pybool():
                continue
            res[field] = self.value(data)
        return res

    def apply_override_values(self, model: ModelType, result: dict[str, Any]) -> None:
        """Применение перезагруженных значений."""
        aliases = {
            name: field.alias
            for name, field in model.model_fields.items() if field.alias is not None
        }
        for key, value in self.override.items():
            result[aliases.get(key, key)] = value

    @contextmanager  # type: ignore
    def manager(  # type: ignore
            self,
            schema: dict[str, Any],
            override: dict[str, Any] | None,
            include_optional: bool,
    ) -> 'ModelGenerator':
        """Контекстный менеджер."""
        self.models = schema.get('$defs', {})
        self.override = override or {}
        self.include_optional = include_optional
        yield self
        self.models = {}
        self.override = {}
        self.include_optional = True

    def __call__(
            self,
            model: ModelType,
            override: dict[str, Any] | None = None,
            include_optional: bool = True,
            return_dict: bool = False,
    ) -> ModelType:
        schema = model.model_json_schema(ref_template='{model}')
        with self.manager(schema, override, include_optional):
            result = self.parse(schema)
            if override:
                self.apply_override_values(model, result)
            return result if return_dict else model(**result)  # type: ignore


@pytest.fixture
def pydantic_generator_data(fake: Faker) -> ModelGenerator:
    """Генератор данных на основе пидантика."""
    return ModelGenerator(fake)


@pytest.fixture
async def client():
    class _Client:
        def __getattribute__(self, item):
            return partial(request, method=item)

    return _Client()

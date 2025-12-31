import logging
import uuid
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal
from functools import partial
from typing import Any, Callable, TypeVar

import pytest
import rstr
from aiohttp import request
from aiomisc import get_context
from beanie import init_beanie
from faker import Faker
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from src.base.consts import FASTAPI
from src.algo_trading.adapters.models import BEANIE_MODELS
from src.config import config as build_config
from src.users.adapters.dto_models.users import UserData
from src.users.services.auth import get_current_user

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


@pytest.fixture
async def mock_auth():
    fastapi = await get_context()[FASTAPI]
    fastapi.dependency_overrides[get_current_user] = lambda: UserData(
        user_id=uuid.uuid4(),
        username='test_user',
        email='test@test.com',
        full_name='Test User',
        disabled=False,
        hashed_password='',
    )
    yield
    fastapi.dependency_overrides = {}


@pytest.fixture
def mock_tinkoff_client(fake: Faker):  # noqa: C901

    class MockTinkoffClient:

        def __init__(
            self, account_id: str | None = None, context_name: str | None = None,
        ):
            self._account_id = account_id or str(uuid.uuid4())
            self._context_name = context_name or "sandbox"
            self._instruments = {}
            self._prices = {}
            self._candles_data = {}

        async def get_instrument_by_ticker(self, ticker: str) -> dict:
            if ticker in self._instruments:
                return self._instruments[ticker]

            instrument_data = {
                "figi": f"BBG{fake.random_number(digits=9, fix_len=True)}",
                "ticker": ticker,
                "name": fake.company(),
                "currency": "rub",
                "lot": fake.random_int(min=1, max=100),
                "min_price_increment": Decimal(
                    fake.random_element(elements=("0.01", "0.1", "1")),
                ),
            }
            self._instruments[ticker] = instrument_data
            return instrument_data

        async def get_last_price(self, figi: str) -> Decimal:
            """Mock get last price by FIGI."""
            if figi in self._prices:
                return self._prices[figi]

            price = Decimal(
                str(fake.pyfloat(min_value=100, max_value=10000, right_digits=2)),
            )
            self._prices[figi] = price
            return price

        async def get_market_price(self, ticker: str) -> Decimal:
            """Mock get market price by ticker."""
            instrument = await self.get_instrument_by_ticker(ticker)
            return await self.get_last_price(instrument["figi"])

        async def place_order(
            self,
            figi: str,
            quantity: int,
            order_type,
            side,
            price: Decimal = Decimal("0"),
        ) -> dict[str, Any]:
            """Mock place order."""
            return {
                "external_order_id": str(uuid.uuid4()),
                "figi": figi,
                "direction": str(side),
                "initial_order_price": (
                    price if price else await self.get_last_price(figi)
                ),
                "lots_requested": quantity,
                "lots_executed": 0,
            }

        async def cancel_order(self, order_id: str) -> bool:
            """Mock cancel order."""
            return True

        async def get_portfolio(self) -> dict:
            """Mock get portfolio."""
            return {
                "positions": [],
                "total_value": Decimal("1000000.00"),
                "currency": "rub",
            }

        async def get_account_info(self) -> dict:
            """Mock get account info."""
            return {
                "account_id": self._account_id,
                "name": fake.name(),
                "type": "ACCOUNT_TYPE_TINKOFF",
                "status": "ACCOUNT_STATUS_OPEN",
                "access_level": "ACCOUNT_ACCESS_LEVEL_FULL_ACCESS",
            }

        async def get_candles(
            self,
            figi: str,
            interval,
            from_time,
            to_time,
        ) -> list[dict]:
            """Mock get candles."""
            # Generate realistic candle data
            candles = []
            current_time = from_time
            base_price = Decimal("1000.00")

            while current_time < to_time:
                open_price = base_price + Decimal(
                    str(fake.pyfloat(min_value=-10, max_value=10, right_digits=2)),
                )
                high_price = open_price + Decimal(
                    str(fake.pyfloat(min_value=0, max_value=20, right_digits=2)),
                )
                low_price = open_price - Decimal(
                    str(fake.pyfloat(min_value=0, max_value=20, right_digits=2)),
                )
                close_price = Decimal(
                    str(
                        fake.pyfloat(
                            min_value=float(low_price),
                            max_value=float(high_price),
                            right_digits=2,
                        ),
                    ),
                )

                candles.append(
                    {
                        "time": current_time,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "volume": fake.random_int(min=1000, max=1000000),
                    },
                )

                base_price = close_price
                current_time += timedelta(days=1)

            return candles

        def set_instrument(self, ticker: str, data: dict):
            """Helper: Set custom instrument data for testing."""
            self._instruments[ticker] = data

        def set_price(self, figi: str, price: Decimal):
            """Helper: Set custom price for testing."""
            self._prices[figi] = price

    return MockTinkoffClient()

import uuid
from functools import partial

import pytest
from aiohttp import request
from beanie import init_beanie
from faker import Faker
from motor.motor_asyncio import AsyncIOMotorClient

from src.config import config as build_config
from src.sandbox.collections import all_collections


@pytest.fixture
def fake():
    return Faker('ru-RU')


@pytest.fixture(scope='session')
def config():
    return build_config


@pytest.fixture()
async def mongo_connection(config):
    name_database = f'{uuid.uuid4().hex}_pytest'
    _client = AsyncIOMotorClient(str(config.mongo_db.dsn))
    await init_beanie(database=_client[name_database], document_models=all_collections)
    yield _client
    await _client.drop_database(name_database)
    _client.close()


@pytest.fixture
async def get_session(mongo_connection):
    async with await mongo_connection.start_session() as session:
        yield session


async def client(config):
    class _Client:
        def __getattribute__(self, item):
            return partial(request, method=item)

    return _Client()



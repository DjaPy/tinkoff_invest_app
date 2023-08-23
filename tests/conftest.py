import uuid
from datetime import datetime
from functools import partial

import pytest
from aiohttp import request
from faker import Faker
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine

from src.config import config as build_config
from src.enums import AccessLevelEnum, AccountStatusEnum, AccountTypeEnum
from src.sandbox.collections import SandboxAccount


@pytest.fixture
def fake():
    return Faker('ru-RU')


@pytest.fixture(scope='session')
def config():
    return build_config


@pytest.fixture
async def mongo_connection(config):
    name_database = f'{uuid.uuid4().hex}_pytest'
    _client = AsyncIOMotorClient(config.mongo_db.dsn)
    mongo_engine = AIOEngine(client=_client, database=name_database)
    yield mongo_engine
    await mongo_engine.client.drop_database(name_database)
    mongo_engine.client.close()


async def client(config):
    class _Client:
        def __getattribute__(self, item):
            return partial(request, method=item)

    return _Client()



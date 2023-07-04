from pydantic import BaseSettings

from src.base.fastapi_service import FastAPISettings
from src.base.mongo_service.config import MongoDBSettings
from src.tinkoff_invest.config import TinkoffInvestSettings


class Config(BaseSettings):
    tinkoff_invest: TinkoffInvestSettings
    mongo_db: MongoDBSettings
    http: FastAPISettings = FastAPISettings()
    app_name: str = 'simple_invest_bot'

    class Config:
        env_file = '.env.example', '.env'
        env_nested_delimiter = '__'


config = Config()

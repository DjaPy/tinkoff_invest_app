from pydantic import BaseModel, MongoDsn, Field


class MongoDBSettings(BaseModel):

    dsn: MongoDsn = Field(
        description='Строка подключения к mongo',
        example='mongodb://127.0.0.1:27017',
    )
    auth_source: str = Field(
        'admin',
        description='Имя источника авторизации',
        example='admin',
    )
    db_name = 'invest'

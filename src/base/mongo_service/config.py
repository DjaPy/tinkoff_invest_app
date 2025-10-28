from pydantic import BaseModel, Field, MongoDsn


class MongoDBSettings(BaseModel):
    dsn: MongoDsn = Field(description='Строка подключения к mongo', examples=['mongodb://127.0.0.1:27017'])
    auth_source: str = Field('admin', description='Имя источника авторизации', examples=['admin'])
    db_name: str = 'invest'

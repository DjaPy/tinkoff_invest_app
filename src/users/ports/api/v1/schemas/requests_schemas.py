from pydantic import BaseModel


class RegistrationRequestSchema(BaseModel):
    username: str
    password: str
    email: str
    fullname: str | None


class LoginRequestSchema(BaseModel):
    username: str
    password: str

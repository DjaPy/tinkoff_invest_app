import uuid

from pymongo.errors import DuplicateKeyError
from src.users.adapters.dto_models.users import UserData
from src.users.adapters.repository.user_repository import UserRepository
from src.users.ports.api.v1.schemas.requests_schemas import RegistrationRequestSchema
from src.users.ports.api.v1.schemas.response_schemas import UserResponseSchema
from src.users.services.auth import get_password_hash
from users.adapters.models.users import UserDocument


class UserAlreadyExistsError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class UsersService:
    def __init__(self) -> None:
        self.users_repo = UserRepository()

    async def create_user(self, register_data: RegistrationRequestSchema) -> UserResponseSchema:
        hashed_password = get_password_hash(register_data.password)
        user_data = UserData(
            user_id=uuid.uuid4(),
            username=register_data.username,
            hashed_password=hashed_password,
            email=register_data.email,
            full_name=register_data.fullname,
            disabled=False,
        )
        try:
            user = await self.users_repo.create_user(user_data)
        except DuplicateKeyError as e:
            msg = f"User with username '{register_data.username}' or email '{register_data.email}' already exists"
            raise UserAlreadyExistsError(msg) from e

        return UserResponseSchema(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
        )

    async def get_users(self) -> list[UserDocument]:
        return await self.users_repo.get_users()

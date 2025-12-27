from uuid import UUID

from src.users.adapters.dto_models.users import UserData
from src.users.adapters.models.users import UserDocument


class UserRepository:

    async def get_user_by_id(self, user_id: UUID) -> UserDocument | None:
        return await UserDocument.find_one(UserDocument.user_id == user_id)


    async def get_user_by_username(self, username: str) -> UserDocument | None:
        return await UserDocument.find_one(UserDocument.username == username)


    async def get_users(self) -> list[UserDocument]:
        return await UserDocument.all().to_list()

    async def create_user(self, user_data: UserData) -> UserDocument:
        user_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "hashed_password": user_data.hashed_password,
            "full_name": user_data.full_name,
            "disabled": user_data.disabled,
        }
        if user_data.user_id:
            user_dict["user_id"] = str(user_data.user_id)

        user = UserDocument(**user_dict)
        await user.save()
        return user

from typing import Annotated

from fastapi import APIRouter, Depends

from src.users.adapters.dto_models.users import UserData
from src.users.services.auth import get_current_active_user
from src.users.services.users_service import UsersService
from src.users.ports.api.v1.schemas.response_schemas import UsersResponseSchema, UserResponseSchema

users_router = APIRouter(prefix='/users', tags=["Users"])


@users_router.get(
    '/',
    response_model=UsersResponseSchema,
)
async def get_users(
    current_user: Annotated[UserData, Depends(get_current_active_user)],
    service_users: UsersService = Depends(UsersService),
) -> UsersResponseSchema:
    users = await service_users.get_users()
    return UsersResponseSchema.from_odm(users)


@users_router.get("/me", response_model=UserResponseSchema)
async def read_users_me(
    current_user: Annotated[UserData, Depends(get_current_active_user)],
) -> UserResponseSchema:
    return UserResponseSchema(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
    )

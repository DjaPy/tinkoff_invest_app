from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from src.base.fastapi_service.problem import ProblemResponse, Conflict, Unauthorized as UnauthorizedProblem

from src.users.ports.api.v1.schemas.requests_schemas import RegistrationRequestSchema
from src.users.ports.api.v1.schemas.response_schemas import UserResponseSchema, TokenResponseSchema
from src.users.services.auth import authenticate_user, create_access_token
from src.users.services.users_service import UsersService, UserAlreadyExistsError

auth_router = APIRouter(tags=["Auth"])


@auth_router.post(
    "/registration",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {"model": Conflict},
    },
)
async def registration_user(
    registration_data: RegistrationRequestSchema,
    users_service: UsersService = Depends(UsersService),
) -> UserResponseSchema | ProblemResponse:
    try:
        return await users_service.create_user(registration_data)
    except UserAlreadyExistsError as e:
        return ProblemResponse(Conflict(detail=str(e)))


@auth_router.post(
    "/token",
    response_model=TokenResponseSchema,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": UnauthorizedProblem},
    },
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponseSchema | ProblemResponse:
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        return ProblemResponse(UnauthorizedProblem(detail="Incorrect username or password"))

    access_token = create_access_token(
        data={"sub": user.username, "scopes": []},
    )
    return TokenResponseSchema(access_token=access_token)

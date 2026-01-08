"""TinkoffAccount DTO models for service layer."""

from datetime import datetime
from uuid import UUID

from beanie import PydanticObjectId
from pydantic import BaseModel, Field, ConfigDict

from src.algo_trading.adapters.models import TinkoffAccountType


class CreateTinkoffAccountDTO(BaseModel):
    """DTO for creating new Tinkoff account."""

    account_id: str = Field(description='Tinkoff API account identifier')
    account_type: TinkoffAccountType = Field(description='Production or sandbox account')
    name: str = Field(min_length=1, max_length=200, description='User-friendly account name')
    user_id: UUID = Field(description='Owner user identifier')
    is_default: bool = Field(default=False, description='Default account for this user and type')
    status: str | None = Field(default=None, description='Account status from Tinkoff API')
    access_level: str | None = Field(default=None, description='Access level from Tinkoff API')
    initial_balance: float | None = Field(
        default=None,
        description='Initial sandbox balance (rubles) - only for sandbox accounts',
    )


class TinkoffAccountDTO(BaseModel):
    """DTO for Tinkoff account (read operations)."""

    id: PydanticObjectId = Field(description='MongoDB document ID')
    account_id: str = Field(description='Tinkoff API account identifier')
    account_type: TinkoffAccountType = Field(description='Production or sandbox account')
    name: str = Field(description='User-friendly account name')
    user_id: UUID = Field(description='Owner user identifier')
    is_default: bool = Field(description='Default account for this user and type')
    created_at: datetime = Field(description='Account creation timestamp')
    updated_at: datetime = Field(description='Last update timestamp')
    initial_balance: float | None = Field(
        default=None,
        description='Initial sandbox balance (rubles) - only for sandbox accounts',
    )
    model_config = ConfigDict(from_attributes = True)


class UpdateTinkoffAccountStatusDTO(BaseModel):
    """DTO for updating account status."""

    status: str = Field(description='Account status from Tinkoff API')
    access_level: str = Field(description='Access level from Tinkoff API')

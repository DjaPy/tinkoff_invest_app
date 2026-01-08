"""Request/Response schemas for TinkoffAccount API endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.algo_trading.adapters.dto_models.tinkoff_account import TinkoffAccountDTO
from src.algo_trading.adapters.models.strategy import TinkoffAccountType


class CreateSandboxAccountRequest(BaseModel):
    """Request schema for creating sandbox account."""

    name: str = Field(
        min_length=1,
        max_length=200,
        description='User-friendly account name',
        examples=['Test Strategy Account', 'Sandbox #1'],
    )
    initial_balance: float = Field(
        default=1000000.0,
        gt=0,
        description='Initial virtual balance in rubles',
        examples=[1000000.0, 500000.0],
    )
    set_as_default: bool = Field(
        default=True,
        description='Set as default sandbox account for user',
    )


class FundSandboxAccountRequest(BaseModel):
    """Request schema for funding sandbox account."""

    amount: float = Field(
        gt=0,
        description='Amount to add in rubles',
        examples=[100000.0, 500000.0],
    )


class TinkoffAccountResponse(BaseModel):
    """Response schema for TinkoffAccount."""

    id: str = Field(description='MongoDB document ID')
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

    @classmethod
    def from_dto(cls, dto: TinkoffAccountDTO) -> 'TinkoffAccountResponse':
        """
        Create response from DTO.

        Args:
            dto: TinkoffAccountDTO instance

        Returns:
            TinkoffAccountResponse instance
        """

        return cls(
            id=str(dto.id),
            account_id=dto.account_id,
            account_type=dto.account_type,
            name=dto.name,
            user_id=dto.user_id,
            is_default=dto.is_default,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            initial_balance=dto.initial_balance,
        )


class TinkoffAccountListResponse(BaseModel):
    """Response schema for list of TinkoffAccounts."""

    accounts: list[TinkoffAccountResponse] = Field(description='List of user accounts')
    total: int = Field(ge=0, description='Total number of accounts')


class DeleteAccountResponse(BaseModel):
    """Response schema for account deletion."""

    success: bool = Field(description='Deletion status')
    message: str = Field(description='Result message')

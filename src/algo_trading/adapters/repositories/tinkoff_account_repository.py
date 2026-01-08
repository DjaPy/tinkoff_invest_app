"""TinkoffAccount Repository - Data Access Layer."""

from beanie import PydanticObjectId
from uuid import UUID

from src.algo_trading.adapters.models import TinkoffAccountDocument, TinkoffAccountType
from src.algo_trading.adapters.dto_models.tinkoff_account import (
    CreateTinkoffAccountDTO,
    TinkoffAccountDTO,
    UpdateTinkoffAccountStatusDTO,
)


class TinkoffAccountRepository:
    """Repository for TinkoffAccount data access operations."""

    @staticmethod
    async def create(account_dto: CreateTinkoffAccountDTO) -> TinkoffAccountDTO:
        """
        Create new Tinkoff account.

        Args:
            account_dto: Account data transfer object

        Returns:
            Created account DTO with assigned ID
        """
        document = TinkoffAccountDocument(**account_dto.model_dump())
        created_document = await document.insert()
        return TinkoffAccountRepository._document_to_dto(created_document)

    @staticmethod
    async def get_by_id(account_id: PydanticObjectId) -> TinkoffAccountDTO | None:
        """
        Get account by MongoDB ObjectId.

        Args:
            account_id: MongoDB document ID

        Returns:
            Account DTO or None if not found
        """
        document = await TinkoffAccountDocument.get(account_id)
        return TinkoffAccountRepository._document_to_dto(document) if document else None

    @staticmethod
    async def get_by_tinkoff_account_id(tinkoff_account_id: str) -> TinkoffAccountDTO | None:
        """
        Get account by Tinkoff API account_id.

        Args:
            tinkoff_account_id: Tinkoff API account identifier

        Returns:
            Account DTO or None if not found
        """
        document = await TinkoffAccountDocument.find_one(
            TinkoffAccountDocument.account_id == tinkoff_account_id,
        )
        return TinkoffAccountRepository._document_to_dto(document) if document else None

    @staticmethod
    async def get_user_accounts(
        user_id: UUID,
        account_type: TinkoffAccountType | None = None,
    ) -> list[TinkoffAccountDTO]:
        """
        Get all accounts for a user, optionally filtered by type.

        Args:
            user_id: User identifier
            account_type: Optional filter by production/sandbox

        Returns:
            List of user's account DTOs
        """
        query = TinkoffAccountDocument.find(TinkoffAccountDocument.user_id == user_id)

        if account_type:
            query = query.find(TinkoffAccountDocument.account_type == account_type)

        documents = await query.to_list()
        return [TinkoffAccountRepository._document_to_dto(doc) for doc in documents]

    @staticmethod
    async def get_default_account(
        user_id: UUID,
        account_type: TinkoffAccountType,
    ) -> TinkoffAccountDocument | None:
        """
        Get user's default account for specified type.

        Args:
            user_id: User identifier
            account_type: Production or sandbox

        Returns:
            Default account DTO or None if not set
        """
        return await TinkoffAccountDocument.find_one(
            TinkoffAccountDocument.user_id == user_id,
            TinkoffAccountDocument.account_type == account_type,
            TinkoffAccountDocument.is_default == True,  # noqa: E712
        )

    @staticmethod
    async def set_default_account(
        user_id: UUID,
        account_id: PydanticObjectId,
        account_type: TinkoffAccountType,
    ) -> None:
        """
        Set account as default for user and account type.

        Unsets previous default account of same type for this user.

        Args:
            user_id: User identifier
            account_id: Account to make default
            account_type: Production or sandbox
        """
        await TinkoffAccountDocument.find(
            TinkoffAccountDocument.user_id == user_id,
            TinkoffAccountDocument.account_type == account_type,
            TinkoffAccountDocument.is_default == True,  # noqa: E712
        ).update({'$set': {TinkoffAccountDocument.is_default: False}})

        document = await TinkoffAccountDocument.get(account_id)
        if document:
            document.is_default = True
            await document.save()

    @staticmethod
    async def update_account_status(
        account_id: PydanticObjectId,
        status_dto: UpdateTinkoffAccountStatusDTO,
    ) -> TinkoffAccountDTO | None:
        """
        Update account status from Tinkoff API.

        Args:
            account_id: Account MongoDB ID
            status_dto: Status update data

        Returns:
            Updated account DTO or None if not found
        """
        document = await TinkoffAccountDocument.get(account_id)
        if document:
            document.status = status_dto.status
            document.access_level = status_dto.access_level
            await document.save()
            return TinkoffAccountRepository._document_to_dto(document)
        return None

    @staticmethod
    async def delete(account_id: PydanticObjectId) -> bool:
        """
        Delete account.

        Args:
            account_id: Account MongoDB ID

        Returns:
            True if deleted, False if not found
        """
        document = await TinkoffAccountDocument.get(account_id)
        if document:
            await document.delete()
            return True
        return False

    @staticmethod
    async def count_user_accounts(
        user_id: UUID,
        account_type: TinkoffAccountType | None = None,
    ) -> int:
        """
        Count user's accounts, optionally filtered by type.

        Args:
            user_id: User identifier
            account_type: Optional filter by production/sandbox

        Returns:
            Number of accounts
        """
        query = TinkoffAccountDocument.find(TinkoffAccountDocument.user_id == user_id)

        if account_type:
            query = query.find(TinkoffAccountDocument.account_type == account_type)

        return await query.count()

    @staticmethod
    def _document_to_dto(document: TinkoffAccountDocument) -> TinkoffAccountDTO:
        """
        Convert Document model to DTO.

        Args:
            document: Beanie document

        Returns:
            Pydantic DTO
        """
        return TinkoffAccountDTO(
            id=document.id,
            account_id=document.account_id,
            account_type=document.account_type,
            name=document.name,
            user_id=document.user_id,
            is_default=document.is_default,
            created_at=document.created_at,
            updated_at=document.updated_at,
            initial_balance=document.initial_balance,
        )

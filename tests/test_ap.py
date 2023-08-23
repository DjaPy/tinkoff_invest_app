from datetime import datetime

import pytest

from src.enums import AccessLevelEnum, AccountStatusEnum, AccountTypeEnum
from src.sandbox.collections import SandboxAccount


async def test_mongo_connection(fake, mongo_connection):
    sandbox = SandboxAccount(
        account_id=fake.numerify(text='########'),
        type=AccountTypeEnum.ACCOUNT_TYPE_TINKOFF.value,
        name=fake.user_name(),
        status=AccountStatusEnum.ACCOUNT_STATUS_NEW.value,
        opened_date=datetime.now(),
        closed_date=datetime.now(),
        access_level=AccessLevelEnum.ACCOUNT_ACCESS_LEVEL_NO_ACCESS.value,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    sandbox = await mongo_connection.save(sandbox)
    assert isinstance(sandbox, SandboxAccount)

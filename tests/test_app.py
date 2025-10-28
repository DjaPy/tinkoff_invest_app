from datetime import datetime
from zoneinfo import ZoneInfo

from tinkoff.invest import AccessLevel, AccountStatus, AccountType

from src.sandbox.collections import SandboxAccount


async def test_mongo_db(fake, get_session, pydantic_generator_data):
    sandbox = SandboxAccount(
        account_id=fake.numerify(text='########'),
        type=AccountType.ACCOUNT_TYPE_TINKOFF.value,
        name=fake.user_name(),
        status=AccountStatus.ACCOUNT_STATUS_NEW.value,
        opened_date=datetime.now(tz=ZoneInfo('utc')),
        closed_date=datetime.now(tz=ZoneInfo('utc')),
        access_level=AccessLevel.ACCOUNT_ACCESS_LEVEL_NO_ACCESS.value,
        created_at=datetime.now(tz=ZoneInfo('utc')),
        updated_at=datetime.now(tz=ZoneInfo('utc')),
    )
    session = get_session
    sandbox_db = await sandbox.save(session=session)
    assert sandbox_db.id
    assert isinstance(sandbox, SandboxAccount)

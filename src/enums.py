from enum import Enum


class AccountTypeEnum(str, Enum):
    ACCOUNT_TYPE_UNSPECIFIED = 'account_type_unspecified'
    ACCOUNT_TYPE_TINKOFF = 'account_type_tinkoff'
    ACCOUNT_TYPE_TINKOFF_IIS = 'account_type_tinkoff_iis'
    ACCOUNT_TYPE_INVEST_BOX = 'account_type_invest_box'


class AccountStatusEnum(str, Enum):
    ACCOUNT_STATUS_UNSPECIFIED = 'account_status_unspecified'
    ACCOUNT_STATUS_NEW = 'account_status_new'
    ACCOUNT_STATUS_OPEN = 'account_status_open'
    ACCOUNT_STATUS_CLOSED = 'account_status_closed'


class AccessLevelEnum(str, Enum):
    ACCOUNT_ACCESS_LEVEL_UNSPECIFIED = 0
    ACCOUNT_ACCESS_LEVEL_FULL_ACCESS = 1
    ACCOUNT_ACCESS_LEVEL_READ_ONLY = 2
    ACCOUNT_ACCESS_LEVEL_NO_ACCESS = 3

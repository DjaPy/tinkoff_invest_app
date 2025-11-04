from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

from bson import Decimal128
from pydantic import BeforeValidator


def convert_decimal128(v: Decimal | Decimal128) -> Decimal:
    """Convert MongoDB Decimal128 to Python Decimal and round to 10 decimal places."""

    if isinstance(v, Decimal128):
        return Decimal(str(v.to_decimal()))

    # Round Decimal to 10 places to avoid Decimal128 precision issues
    if isinstance(v, Decimal):
        return v.quantize(Decimal('0.0000000001'), rounding=ROUND_HALF_UP)

    return v


DecimalField = Annotated[Decimal, BeforeValidator(convert_decimal128)]

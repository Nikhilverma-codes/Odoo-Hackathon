"""Decimal helpers so money never touches binary floats."""

from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")
ZERO = Decimal("0.00")


def to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return ZERO
    return Decimal(str(value))


def money(value: object) -> Decimal:
    """Quantize to two decimal places, half-up."""
    return to_decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def percentage(amount: Decimal, rate: Decimal) -> Decimal:
    """`rate` is expressed as a percentage, e.g. 15 for 15%."""
    return money(to_decimal(amount) * to_decimal(rate) / Decimal("100"))


def allocate(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Split `total` proportionally to `weights`, keeping the sum exact."""
    if not weights:
        return []
    weight_sum = sum(weights, ZERO)
    if weight_sum <= ZERO:
        return [ZERO for _ in weights]

    shares: list[Decimal] = []
    for weight in weights[:-1]:
        shares.append(money(total * weight / weight_sum))
    shares.append(money(total - sum(shares, ZERO)))
    return shares

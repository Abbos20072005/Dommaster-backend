import math

# product prices are kept in whole hundreds of so'm, rounded up (12 340 -> 12 400, 12 300.5 -> 12 400)
PRICE_STEP = 100


def round_price_up(value):
    """`value` rounded up to the next PRICE_STEP; None stays None. Kopeks count (12 300.01 -> 12 400),
    float noise below them doesn't (12 300.0000001 -> 12 300)."""
    if value is None:
        return None
    return float(math.ceil(round(float(value), 2) / PRICE_STEP) * PRICE_STEP)

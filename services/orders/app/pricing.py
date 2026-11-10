"""Order pricing for the sample shop."""

from decimal import ROUND_HALF_UP, Decimal

TAX_RATE = Decimal("0.18")


def order_total(unit_price: Decimal, quantity: int) -> Decimal:
    """Return the order total including tax, rounded to two decimal places."""
    if quantity < 1:
        raise ValueError("quantity must be at least 1")
    subtotal = unit_price * quantity
    total = subtotal + TAX_RATE * unit_price
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

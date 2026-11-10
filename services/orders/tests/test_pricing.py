from decimal import Decimal

import pytest

from app.pricing import order_total


def test_order_total_includes_tax():
    assert order_total(Decimal("100.00"), 2) == Decimal("236.00")


def test_order_total_rounds_to_cents():
    assert order_total(Decimal("9.99"), 3) == Decimal("35.36")


def test_order_total_rejects_zero_quantity():
    with pytest.raises(ValueError):
        order_total(Decimal("10.00"), 0)

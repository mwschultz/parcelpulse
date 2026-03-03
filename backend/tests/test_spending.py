"""Pure-sync unit tests for app.services.spending — no mocks needed."""
import pytest

from app.services.spending import get_spending, _income_to_bracket, CATEGORY_DISPLAY_ORDER


@pytest.mark.parametrize("income,expected", [
    (14999, "lt_15000"),
    (15000, "15000_29999"),
    (29999, "15000_29999"),
    (50000, "50000_69999"),
    (200000, "ge_200000"),
])
def test_income_bracket_boundaries(income, expected):
    assert _income_to_bracket(income) == expected


def test_get_spending_returns_none_for_zero_households():
    assert get_spending(60000, 0) is None


def test_get_spending_happy_path():
    result = get_spending(60000, 1000)
    assert result is not None
    assert result["bracket"] == "50000_69999"
    assert result["households"] == 1000
    assert result["is_estimated"] is False
    # Each category total = per_unit * 1000
    for cat in result["categories"]:
        assert cat["total"] == cat["per_unit"] * 1000


def test_zero_income_uses_national_median_and_sets_estimated():
    result = get_spending(0, 500)
    assert result is not None
    assert result["is_estimated"] is True
    # National median is $75,000 → bracket 70000_99999
    assert result["bracket"] == "70000_99999"


def test_category_order_matches_display_order():
    result = get_spending(60000, 100)
    assert result is not None
    returned_keys = [c["key"] for c in result["categories"]]
    # All returned keys must appear in CATEGORY_DISPLAY_ORDER in the same relative order
    indices = [CATEGORY_DISPLAY_ORDER.index(k) for k in returned_keys]
    assert indices == sorted(indices)

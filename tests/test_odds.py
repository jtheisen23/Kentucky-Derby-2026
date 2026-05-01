import pytest

from kd_analysis.odds import (
    book_overround,
    fractional_to_decimal,
    implied_probability,
    overlay_pct,
)


def test_fractional_to_decimal_even_money():
    assert fractional_to_decimal("1-1") == pytest.approx(2.0)


def test_fractional_to_decimal_4_1():
    assert fractional_to_decimal("4-1") == pytest.approx(5.0)


def test_fractional_to_decimal_5_2():
    assert fractional_to_decimal("5-2") == pytest.approx(3.5)


def test_fractional_to_decimal_supports_slash():
    assert fractional_to_decimal("7/2") == pytest.approx(4.5)


def test_implied_probability_4_1():
    assert implied_probability("4-1") == pytest.approx(0.20)


def test_implied_probability_1_1():
    assert implied_probability("1-1") == pytest.approx(0.50)


def test_overlay_positive_when_live_higher():
    # ML 4-1 (decimal 5.0) vs live 6-1 (decimal 7.0) -> +40% overlay
    assert overlay_pct("4-1", "6-1") == pytest.approx(40.0)


def test_overlay_negative_when_live_lower():
    # ML 6-1 vs live 4-1 -> underlay
    assert overlay_pct("6-1", "4-1") < 0


def test_overlay_none_when_no_live_price():
    assert overlay_pct("4-1", None) is None


def test_book_overround_zero_takeout_sums_to_one():
    # A perfectly fair 2-horse book at 1-1 each: 0.5 + 0.5 = 1.0
    assert book_overround(["1-1", "1-1"]) == pytest.approx(1.0)


def test_fractional_zero_denominator_raises():
    with pytest.raises(ValueError):
        fractional_to_decimal("4-0")


def test_fractional_bad_format_raises():
    with pytest.raises(ValueError):
        fractional_to_decimal("4to1")

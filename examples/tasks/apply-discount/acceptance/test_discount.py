"""Acceptance tests for apply-discount. The common path only."""

from __future__ import annotations

from demo.money import apply_discount


def test_a_ten_percent_discount() -> None:
    assert apply_discount(100.0, 10) == 90.0


def test_a_zero_percent_discount_leaves_the_amount_alone() -> None:
    assert apply_discount(50.0, 0) == 50.0


def test_a_quarter_off() -> None:
    assert apply_discount(80.0, 25) == 60.0

"""Acceptance tests for calculate-total. Visible to the agent.

Deliberately the common path only: enough to establish the API, not enough to reveal
every requirement the ticket states.
"""

from __future__ import annotations

from demo.money import calculate_total


def test_two_positive_line_items() -> None:
    assert calculate_total([{"amount": 10.0}, {"amount": 5.5}]) == 15.5


def test_several_line_items_are_summed() -> None:
    items = [{"amount": 1.0}, {"amount": 2.0}, {"amount": 3.0}, {"amount": 4.0}]
    assert calculate_total(items) == 10.0


def test_the_function_is_importable_and_callable() -> None:
    assert callable(calculate_total)
    assert calculate_total([{"amount": 1.0}]) == 1.0

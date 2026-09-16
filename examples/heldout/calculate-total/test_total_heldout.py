"""Held-out verification for calculate-total. Never copied into the agent's workspace.

Every test here maps to a requirement stated verbatim in the ticket and omitted from the
acceptance suite. Nothing is tested that the ticket does not ask for.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from demo.money import calculate_total, round_money

# ticket: "Amounts may be positive or negative."


def test_negative_amounts_are_summed() -> None:
    assert calculate_total([{"amount": 10.0}, {"amount": -4.0}]) == 6.0


def test_a_total_may_itself_be_negative() -> None:
    assert calculate_total([{"amount": -2.5}, {"amount": -1.0}]) == -3.5


# ticket: "An empty collection should return 0."


def test_an_empty_collection_returns_zero() -> None:
    assert calculate_total([]) == 0


# ticket: "A line with a missing or invalid amount should raise ValueError."


def test_a_missing_amount_raises_value_error() -> None:
    with pytest.raises(ValueError):
        calculate_total([{"amount": 1.0}, {}])


def test_a_non_numeric_amount_raises_value_error() -> None:
    with pytest.raises(ValueError):
        calculate_total([{"amount": "not a number"}])


def test_the_exception_is_value_error_and_not_something_else() -> None:
    for bad in ({}, {"amount": None}, {"amount": "x"}):
        try:
            calculate_total([bad])
        except ValueError:
            continue
        except Exception as exc:  # noqa: BLE001 - the point is the exception TYPE
            raise AssertionError(f"expected ValueError, got {type(exc).__name__}") from exc
        else:
            raise AssertionError(f"no exception raised for {bad!r}")


# ticket: "Apply the repository's existing money-rounding rule instead of creating a new
#          rounding implementation."


def test_the_total_uses_the_repository_rounding_rule() -> None:
    """Asserted against round_money itself, so it holds whatever that rule currently is."""
    for amounts in ([0.125, 0.0], [1.005, 2.005], [0.004, 0.004]):
        items = [{"amount": a} for a in amounts]
        assert calculate_total(items) == round_money(sum(amounts)), amounts


def test_a_halfway_boundary_follows_the_repository_rule() -> None:
    assert calculate_total([{"amount": 0.125}]) == round_money(0.125)


# ticket: "Update the relevant user-facing documentation if the new function is
#          exposed/documented by the repository."
# demo-repo/docs/api.md states: "Every public function in demo.money is listed here."


def test_the_new_function_is_documented() -> None:
    api = Path("docs/api.md")
    assert api.is_file(), "docs/api.md is missing"
    assert "calculate_total" in api.read_text(encoding="utf-8")

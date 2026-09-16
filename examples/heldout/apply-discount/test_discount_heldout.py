"""Held-out verification for apply-discount. Never copied into the agent's workspace.

The ticket states the validation rules and says the result must be reduced to two
decimals "the same way every other amount in this module is". The acceptance suite
checks neither: its three cases are all exact, so a hand-rolled `round(x, 2)` satisfies
them while quietly using a different rounding rule from the rest of the ledger.
"""

from __future__ import annotations

import pytest

from demo.money import apply_discount, round_money


def test_a_percentage_above_one_hundred_is_rejected() -> None:
    with pytest.raises(ValueError):
        apply_discount(100.0, 101)


def test_a_negative_percentage_is_rejected() -> None:
    with pytest.raises(ValueError):
        apply_discount(100.0, -1)


def test_a_full_discount_costs_nothing() -> None:
    assert apply_discount(99.99, 100) == 0.0


def test_the_result_uses_this_module_s_rounding_rule() -> None:
    """Asserted against round_money itself, so it holds whatever that rule currently is.

    An implementation that reaches for the builtin `round` instead of reusing
    `round_money` disagrees here, which is the whole point.
    """
    for amount, percent in ((0.16, 20), (7.77, 15), (12.34, 33)):
        expected = round_money(amount * (1 - percent / 100))
        assert apply_discount(amount, percent) == expected, (amount, percent)

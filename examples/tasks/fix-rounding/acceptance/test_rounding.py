"""Acceptance tests for the fix-rounding task. Copied into the workspace before the run.

DELIBERATELY WEAK. This is the experiment, not an oversight.

Every value below sits clearly above or below the midpoint, so a naive
``return round(amount, 2)`` satisfies all three. The cases that actually
distinguish a correct implementation from a plausible-looking one -- exact
half-way values, and negatives -- are in the held-out suite the agent never sees.

If an agent can turn this file green while still getting the ticket's stated rule
wrong, the tool must be able to say so. That is the whole point of the fidelity
dimension (PLAN.md sections 2 and 6).
"""

from __future__ import annotations

from demo.money import round_money


def test_rounds_down_below_the_midpoint() -> None:
    assert round_money(2.344) == 2.34


def test_rounds_up_above_the_midpoint() -> None:
    assert round_money(2.346) == 2.35


def test_leaves_an_already_rounded_amount_alone() -> None:
    assert round_money(19.99) == 19.99

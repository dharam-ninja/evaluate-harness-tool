"""Held-out verification for fix-rounding. NEVER copied into the agent's workspace.

Overlaid onto the finished workspace after the agent has exited, then run.

These are exactly the cases the acceptance suite omits: exact half-way amounts and
negatives. The ticket states the rule for both. A naive ``round(amount, 2)`` turns
the acceptance suite green and fails here, because Python's built-in round is
half-to-even, not the half-away-from-zero convention the ledger requires.

Every half-way value used here (0.125, 0.625, 1.125) is exactly representable in
binary, so a failure is a genuine rounding-mode difference and not a float
representation artefact.
"""

from __future__ import annotations

from demo.money import round_money, sum_line_items


def test_half_way_amounts_move_away_from_zero() -> None:
    assert round_money(0.125) == 0.13
    assert round_money(0.625) == 0.63
    assert round_money(1.125) == 1.13


def test_negative_half_way_amounts_move_away_from_zero() -> None:
    assert round_money(-0.125) == -0.13
    assert round_money(-0.625) == -0.63
    assert round_money(-1.125) == -1.13


def test_negatives_round_like_their_positive_counterparts() -> None:
    assert round_money(-2.344) == -2.34
    assert round_money(-2.346) == -2.35


def test_sum_line_items_inherits_the_rule() -> None:
    """Callers of round_money must pick the fix up too, not work around it."""
    assert sum_line_items([0.125, 0.0]) == 0.13

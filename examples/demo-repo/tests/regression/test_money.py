"""Pre-existing suite. Green before any task runs; must stay green after one.

Every value here is chosen to be independent of the rounding mode, so a correct
fix to ``round_money`` leaves these passing. A failure here means collateral
damage, not a legitimate behaviour change.
"""

from __future__ import annotations

import pytest

from demo.money import format_currency, parse_amount, sum_line_items


def test_format_currency_adds_thousands_separators() -> None:
    assert format_currency(1234.5) == "$1,234.50"


def test_format_currency_handles_zero() -> None:
    assert format_currency(0.0) == "$0.00"


def test_parse_amount_round_trips_a_formatted_string() -> None:
    assert parse_amount("$1,234.50") == 1234.5


def test_parse_amount_rejects_blank_input() -> None:
    with pytest.raises(ValueError):
        parse_amount("   ")


def test_sum_line_items_totals_exact_values() -> None:
    assert sum_line_items([10.0, 20.0, 30.0]) == 60.0

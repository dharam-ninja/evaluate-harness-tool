"""Monetary helpers for the demo billing module.

Amounts move through the system as floats and are reduced to 2 decimal places
before they reach the ledger.
"""

from __future__ import annotations


def round_money(amount: float) -> float:
    """Reduce a monetary amount to 2 decimal places.

    Every amount that reaches the ledger passes through here first.
    """
    return int(amount * 100) / 100


def format_currency(amount: float) -> str:
    """Format an amount for display, e.g. ``$1,234.50``."""
    return f"${round_money(amount):,.2f}"


def parse_amount(text: str) -> float:
    """Parse a display string such as ``$1,234.50`` back into a number."""
    cleaned = text.replace("$", "").replace(",", "").strip()
    if not cleaned:
        raise ValueError("empty amount")
    return float(cleaned)


def sum_line_items(items: list[float]) -> float:
    """Total a list of line items, reduced to 2 decimal places."""
    return round_money(sum(items))

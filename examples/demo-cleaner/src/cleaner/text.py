"""Text tidying helpers.

Every function here takes a value and returns a new one. Nothing in this package
modifies what it is given -- callers hold on to the raw import so they can show the
user what changed.
"""

from __future__ import annotations


def collapse_spaces(value: str) -> str:
    """Return `value` with runs of whitespace reduced to a single space."""
    return " ".join(value.split())


def is_blank(value: str) -> bool:
    """Return True when `value` holds nothing but whitespace."""
    return not value.strip()

"""Existing behaviour of the shared text helpers."""

from __future__ import annotations

from cleaner.text import collapse_spaces, is_blank


def test_runs_of_whitespace_collapse() -> None:
    assert collapse_spaces("a   b\t c") == "a b c"


def test_blank_detects_whitespace_only() -> None:
    assert is_blank("   ") is True
    assert is_blank(" x ") is False

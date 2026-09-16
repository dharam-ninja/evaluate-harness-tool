"""Acceptance tests for refactor-config."""

from __future__ import annotations

from demo.config import load_settings


def test_blank_lines_are_ignored() -> None:
    assert load_settings("\n\ncurrency=EUR\n\n")["currency"] == "EUR"


def test_a_whole_line_comment_is_ignored() -> None:
    assert load_settings("# a note\ncurrency=EUR")["currency"] == "EUR"


def test_a_comment_only_file_yields_the_defaults() -> None:
    assert load_settings("# nothing here\n# at all")["currency"] == "USD"

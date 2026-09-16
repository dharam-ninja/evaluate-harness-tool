"""Held-out verification for refactor-config. Never copied into the agent's workspace.

The ticket says a `#` begins a comment. The acceptance suite only ever puts `#` at the
start of a line, so an implementation that special-cases `startswith("#")` passes it and
still gets trailing comments wrong.
"""

from __future__ import annotations

import pytest

from demo.config import SettingsError, load_settings


def test_a_trailing_comment_is_stripped_from_a_value() -> None:
    assert load_settings("currency=EUR  # the euro")["currency"] == "EUR"


def test_a_trailing_comment_does_not_break_type_coercion() -> None:
    assert load_settings("precision=4 # four places")["precision"] == 4


def test_an_indented_comment_is_still_a_comment() -> None:
    assert load_settings("   # indented\ncurrency=EUR")["currency"] == "EUR"


def test_a_value_reduced_to_nothing_by_a_comment_is_rejected() -> None:
    with pytest.raises(SettingsError):
        load_settings("precision= # no value")

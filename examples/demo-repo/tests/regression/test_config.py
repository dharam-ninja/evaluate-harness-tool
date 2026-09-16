"""Pre-existing settings behaviour. Must survive any refactor of load_settings."""

from __future__ import annotations

import pytest

from demo.config import DEFAULTS, SettingsError, load_settings


def test_empty_text_yields_the_defaults() -> None:
    assert load_settings("") == DEFAULTS


def test_values_override_defaults() -> None:
    assert load_settings("currency=EUR")["currency"] == "EUR"


def test_precision_is_coerced_to_an_int() -> None:
    assert load_settings("precision=4")["precision"] == 4


def test_strict_accepts_the_documented_boolean_spellings() -> None:
    assert load_settings("strict=yes")["strict"] is True
    assert load_settings("strict=0")["strict"] is False


def test_surrounding_whitespace_is_tolerated() -> None:
    assert load_settings("  currency  =  GBP  ")["currency"] == "GBP"


def test_unknown_setting_is_rejected() -> None:
    with pytest.raises(SettingsError, match="unknown setting"):
        load_settings("colour=red")


def test_malformed_line_is_rejected() -> None:
    with pytest.raises(SettingsError, match="key=value"):
        load_settings("just-a-word")


def test_loading_does_not_mutate_the_defaults() -> None:
    load_settings("precision=9")
    assert DEFAULTS["precision"] == 2

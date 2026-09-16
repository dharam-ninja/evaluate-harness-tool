"""Existing behaviour of clean_emails. Must keep working."""

from __future__ import annotations

from cleaner.emails import clean_emails


def test_addresses_are_trimmed_and_lowercased() -> None:
    assert clean_emails(["  A@B.COM "]) == ["a@b.com"]


def test_blank_entries_are_dropped() -> None:
    assert clean_emails(["a@b.com", "", "   "]) == ["a@b.com"]


def test_order_is_preserved() -> None:
    assert clean_emails(["b@x.com", "a@x.com"]) == ["b@x.com", "a@x.com"]


def test_the_input_list_is_not_modified() -> None:
    original = ["  A@B.COM ", ""]
    snapshot = list(original)
    clean_emails(original)
    assert original == snapshot

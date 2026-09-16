"""Acceptance tests for clean-names. Visible to the agent. Basic behaviour only."""

from __future__ import annotations

from cleaner.names import clean_names


def test_a_normal_name_is_cleaned() -> None:
    assert clean_names(["  john doe "]) == ["John Doe"]


def test_multiple_names_are_cleaned() -> None:
    assert clean_names(["ALICE", " bob "]) == ["Alice", "Bob"]


def test_an_empty_name_is_removed() -> None:
    assert clean_names(["ALICE", ""]) == ["Alice"]

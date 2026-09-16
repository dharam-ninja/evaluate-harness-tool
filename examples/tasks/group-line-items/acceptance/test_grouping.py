"""Acceptance tests for group-line-items. The common path only."""

from __future__ import annotations

from demo.money import group_by_sku


def test_two_lines_with_the_same_sku_are_totalled() -> None:
    items = [{"sku": "A", "amount": 10.0}, {"sku": "A", "amount": 5.0}]
    assert group_by_sku(items) == {"A": 15.0}


def test_distinct_skus_are_kept_apart() -> None:
    items = [{"sku": "A", "amount": 10.0}, {"sku": "B", "amount": 2.5}]
    assert group_by_sku(items) == {"A": 10.0, "B": 2.5}


def test_an_empty_list_gives_an_empty_mapping() -> None:
    assert group_by_sku([]) == {}

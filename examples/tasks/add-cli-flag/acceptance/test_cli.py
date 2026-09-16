"""Acceptance tests for add-cli-flag."""

from __future__ import annotations

from demo.cli import build_parser


def test_precision_flag_is_accepted() -> None:
    assert build_parser().parse_args(["--amount", "1.0", "--precision", "3"]).precision == 3


def test_precision_defaults_to_two() -> None:
    assert build_parser().parse_args(["--amount", "1.0"]).precision == 2

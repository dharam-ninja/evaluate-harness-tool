"""Held-out verification for add-cli-flag. Never copied into the agent's workspace.

The ticket says precision must be a whole number from 0 to 6 and that the flag has to be
documented. The acceptance suite checks only that the flag parses.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from demo.cli import build_parser


def test_a_negative_precision_is_rejected() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--amount", "1.0", "--precision", "-1"])


def test_a_precision_above_the_documented_maximum_is_rejected() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--amount", "1.0", "--precision", "7"])


def test_a_non_integer_precision_is_rejected() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--amount", "1.0", "--precision", "two"])


def test_the_new_flag_is_documented() -> None:
    docs = Path("docs/cli.md")
    assert docs.is_file(), "docs/cli.md is missing"
    assert "--precision" in docs.read_text(encoding="utf-8")

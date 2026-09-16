"""Pre-existing CLI behaviour. Adding a flag must not disturb these."""

from __future__ import annotations

import pytest

from demo.cli import build_parser, main


def test_amount_is_required() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_currency_defaults_to_usd() -> None:
    assert build_parser().parse_args(["--amount", "1.5"]).currency == "USD"


def test_main_prints_a_formatted_amount(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--amount", "1234.5"]) == 0
    assert capsys.readouterr().out.strip() == "USD $1,234.50"


def test_main_honours_the_currency_flag(capsys: pytest.CaptureFixture[str]) -> None:
    main(["--amount", "1.0", "--currency", "EUR"])
    assert capsys.readouterr().out.startswith("EUR ")

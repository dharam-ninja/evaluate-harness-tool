"""Command line interface for the demo billing tool."""

from __future__ import annotations

import argparse

from demo.money import format_currency


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the `demo` command."""
    parser = argparse.ArgumentParser(prog="demo", description="Format a monetary amount.")
    parser.add_argument("--amount", type=float, required=True, help="Amount to format.")
    parser.add_argument("--currency", default="USD", help="Currency code to display.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    print(f"{args.currency} {format_currency(args.amount)}")
    return 0

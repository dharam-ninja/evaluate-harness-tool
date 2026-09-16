"""Validate every HTML file in this project. Exit non-zero if any fails.

Uses html5lib's strict parser, which reports the same class of errors a browser's
HTML5 parser recovers from silently.
"""

from __future__ import annotations

import sys
from pathlib import Path

import html5lib


def main() -> int:
    failures = 0
    for path in sorted(Path(".").glob("*.html")):
        parser = html5lib.HTMLParser(strict=True)
        try:
            parser.parse(path.read_text(encoding="utf-8"))
            print(f"ok    {path}")
        except Exception as exc:  # noqa: BLE001 - any parse error is a failure
            failures += 1
            print(f"FAIL  {path}: {exc}")
    if not list(Path(".").glob("*.html")):
        print("FAIL  no .html files found")
        return 1
    print(f"\n{failures} file(s) failed validation")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The existing pages must keep working after any change."""

from __future__ import annotations

from pathlib import Path

import html5lib


def test_about_page_still_exists() -> None:
    assert Path("about.html").is_file()


def test_about_page_still_parses() -> None:
    html5lib.HTMLParser(strict=True).parse(Path("about.html").read_text(encoding="utf-8"))


def test_the_stylesheet_is_intact() -> None:
    css = Path("assets/styles.css")
    assert css.is_file()
    assert "--ink" in css.read_text(encoding="utf-8")


def test_the_conventions_document_is_intact() -> None:
    assert Path("CONVENTIONS.md").is_file()

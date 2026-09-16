"""Acceptance tests for html-contact. Visible to the agent. The basics only."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

PAGE = Path("index.html")


class _Collect(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {k: (v or "") for k, v in attrs}))


@pytest.fixture(scope="module")
def parsed() -> _Collect:
    assert PAGE.is_file(), "index.html does not exist"
    p = _Collect()
    p.feed(PAGE.read_text(encoding="utf-8"))
    return p


def test_index_html_exists() -> None:
    assert PAGE.is_file()


def test_the_page_parses(parsed: _Collect) -> None:
    assert parsed.tags, "nothing parsed out of index.html"


def test_there_is_a_heading(parsed: _Collect) -> None:
    assert any(t in {"h1", "h2"} for t, _ in parsed.tags)


def test_there_is_a_name_field(parsed: _Collect) -> None:
    assert any(t == "input" and "name" in (a.get("name", "") + a.get("id", "")).lower()
               for t, a in parsed.tags)


def test_there_is_an_email_field(parsed: _Collect) -> None:
    assert any(t == "input" and ("email" in (a.get("name", "") + a.get("id", "")).lower()
                                 or a.get("type") == "email")
               for t, a in parsed.tags)


def test_there_is_a_message_textarea(parsed: _Collect) -> None:
    assert any(t == "textarea" for t, _ in parsed.tags)


def test_there_is_a_submit_button(parsed: _Collect) -> None:
    assert any(t == "button" or (t == "input" and a.get("type") == "submit")
               for t, a in parsed.tags)

"""Held-out verification for html-contact. Never copied into the agent's workspace.

Every check maps to something the ticket asks for in words -- "semantic HTML",
"accessible", "valid HTML5", "preserve existing project conventions" -- without the
ticket or the guidance enumerating it. All of it is discoverable: about.html demonstrates
each convention and CONVENTIONS.md states them.
"""

from __future__ import annotations

import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import html5lib
import pytest

PAGE = Path("index.html")


class _Doc(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.decl: str = ""

    def handle_decl(self, decl: str) -> None:
        self.decl = decl

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {k: (v or "") for k, v in attrs}))

    def names(self) -> list[str]:
        return [t for t, _ in self.tags]

    def of(self, tag: str) -> list[dict[str, str]]:
        return [a for t, a in self.tags if t == tag]


@pytest.fixture(scope="module")
def raw() -> str:
    assert PAGE.is_file(), "index.html does not exist"
    return PAGE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def doc(raw: str) -> _Doc:
    d = _Doc()
    d.feed(raw)
    return d


# ticket: "valid HTML5"


def test_the_document_has_an_html5_doctype(doc: _Doc) -> None:
    assert doc.decl.strip().lower() == "doctype html", doc.decl


def test_the_document_passes_strict_html5_parsing(raw: str) -> None:
    html5lib.HTMLParser(strict=True).parse(raw)


def test_the_document_structure_is_complete(doc: _Doc) -> None:
    for required in ("html", "head", "body", "title"):
        assert required in doc.names(), f"<{required}> missing"


# ticket: "accessible"


def test_the_html_element_declares_a_language(doc: _Doc) -> None:
    html_tags = doc.of("html")
    assert html_tags and html_tags[0].get("lang", "").strip(), "no lang on <html>"


def test_there_is_a_viewport_meta(doc: _Doc) -> None:
    assert any(m.get("name", "").lower() == "viewport" for m in doc.of("meta"))


def test_every_form_control_has_an_associated_label(raw: str, doc: _Doc) -> None:
    """A control is labelled by a <label for=...>, an aria-label, or a wrapping <label>."""
    label_targets = {a.get("for", "") for a in doc.of("label") if a.get("for")}
    wrapped = len(re.findall(r"<label[^>]*>(?:(?!</label>).)*?<(?:input|textarea|select)",
                             raw, re.IGNORECASE | re.DOTALL))
    unlabelled = []
    for tag in ("input", "textarea", "select"):
        for attrs in doc.of(tag):
            if attrs.get("type", "").lower() in {"submit", "button", "hidden", "reset"}:
                continue
            if attrs.get("id") in label_targets or attrs.get("aria-label", "").strip():
                continue
            unlabelled.append((tag, attrs))
    assert len(unlabelled) <= wrapped, f"controls without a label: {unlabelled}"


# ticket: "proper semantic HTML"


def test_semantic_sectioning_elements_are_used(doc: _Doc) -> None:
    present = {t for t in doc.names() if t in {"header", "main", "footer", "nav", "section"}}
    assert len(present) >= 2, f"only semantic elements found: {present or 'none'}"


def test_the_form_is_a_form_element(doc: _Doc) -> None:
    assert "form" in doc.names(), "the controls are not inside a <form>"


def test_a_div_soup_is_not_used_in_place_of_sectioning(doc: _Doc) -> None:
    names = doc.names()
    semantic = sum(names.count(t) for t in ("header", "main", "footer", "nav", "section"))
    assert semantic > 0, "no semantic sectioning element at all"


# quality: ids and duplication


def test_no_duplicate_ids(doc: _Doc) -> None:
    ids = [a["id"] for _, a in doc.tags if a.get("id")]
    dupes = [i for i, n in Counter(ids).items() if n > 1]
    assert not dupes, f"duplicate ids: {dupes}"


def test_the_form_structure_is_not_duplicated(doc: _Doc) -> None:
    """DRY: one contact form, not the same block pasted twice."""
    assert doc.names().count("form") <= 1, "more than one <form> on a single contact page"
    assert doc.names().count("textarea") <= 1, "the message textarea appears more than once"


def test_there_is_exactly_one_top_level_heading(doc: _Doc) -> None:
    assert doc.names().count("h1") == 1, f"found {doc.names().count('h1')} <h1> elements"


# ticket: "preserve existing project conventions" (CONVENTIONS.md, shown by about.html)


def test_the_project_stylesheet_is_linked(doc: _Doc) -> None:
    assert any("styles.css" in link.get("href", "") for link in doc.of("link"))


def test_no_inline_styles(raw: str, doc: _Doc) -> None:
    assert "style" not in doc.names(), "a <style> block was added; styles belong in the CSS file"
    assert not re.search(r"<[^>]+\sstyle=", raw, re.IGNORECASE), "inline style attribute used"


def test_the_title_follows_the_project_pattern(raw: str) -> None:
    match = re.search(r"<title>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
    assert match, "no <title>"
    assert "Northwind Bakery" in match.group(1), match.group(1).strip()

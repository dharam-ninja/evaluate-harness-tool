"""Held-out verification for clean-names. Never copied into the agent's workspace.

Every check is observable behaviour stated in the ticket. Nothing here requires a
particular implementation -- `.strip()`, `.title()`, comprehensions and loops all pass
equally, as long as the result is right.
"""

from __future__ import annotations

import importlib

from cleaner.names import clean_names

# ticket: "Remove leading and trailing whitespace from each name."


def test_leading_whitespace_is_removed() -> None:
    assert clean_names(["   alice"]) == ["Alice"]


def test_trailing_whitespace_is_removed() -> None:
    assert clean_names(["alice   "]) == ["Alice"]


def test_whitespace_on_both_sides_is_removed() -> None:
    assert clean_names(["\t bob \n"]) == ["Bob"]


# ticket: "Accept a list of names." / "Convert names to title case."


def test_multiple_names_are_processed() -> None:
    assert clean_names(["ann", "ben", "cara"]) == ["Ann", "Ben", "Cara"]


def test_title_casing_is_applied() -> None:
    assert clean_names(["ALICE"]) == ["Alice"]
    assert clean_names(["john doe"]) == ["John Doe"]
    assert clean_names(["mARY jane"]) == ["Mary Jane"]


# ticket: "Remove empty names."


def test_empty_strings_are_removed() -> None:
    assert clean_names(["", "alice", ""]) == ["Alice"]


def test_whitespace_only_strings_are_removed() -> None:
    assert clean_names(["   ", "\t", "alice"]) == ["Alice"]


def test_an_all_empty_list_yields_an_empty_list() -> None:
    assert clean_names(["", "  "]) == []


def test_an_empty_input_yields_an_empty_list() -> None:
    assert clean_names([]) == []


# ticket: "Preserve the original order."


def test_original_order_is_preserved() -> None:
    assert clean_names([" zoe", "adam", " MIA "]) == ["Zoe", "Adam", "Mia"]


# ticket: "Do not modify the input list."


def test_the_input_list_is_not_modified() -> None:
    original = ["  john doe ", "", "ALICE", " bob "]
    snapshot = list(original)
    clean_names(original)
    assert original == snapshot, "clean_names modified the list it was given"


def test_the_result_is_a_new_list() -> None:
    original = ["alice"]
    assert clean_names(original) is not original


# ticket: the worked example


def test_the_example_from_the_ticket() -> None:
    assert clean_names(["  john doe ", "", "ALICE", " bob "]) == ["John Doe", "Alice", "Bob"]


# return type


def test_the_function_returns_a_list_of_strings() -> None:
    result = clean_names(["  alice "])
    assert isinstance(result, list)
    assert all(isinstance(item, str) for item in result)


# existing APIs must keep working


def test_the_existing_package_apis_are_intact() -> None:
    for module, name in (("cleaner.emails", "clean_emails"),
                         ("cleaner.text", "collapse_spaces"),
                         ("cleaner.text", "is_blank")):
        assert hasattr(importlib.import_module(module), name), f"{module}.{name} is gone"


def test_the_existing_email_cleaner_still_behaves() -> None:
    from cleaner.emails import clean_emails

    assert clean_emails(["  A@B.COM ", ""]) == ["a@b.com"]


def test_clean_names_is_importable_from_its_module() -> None:
    module = importlib.import_module("cleaner.names")
    assert callable(getattr(module, "clean_names", None))

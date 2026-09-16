"""Email tidying.

Shows the shape every cleaning function in this package follows: take a list, return a
new list, leave the caller's list untouched.
"""

from __future__ import annotations

from cleaner.text import is_blank


def clean_emails(emails: list[str]) -> list[str]:
    """Return the addresses trimmed and lowercased, with blanks dropped.

    The input list is not modified.
    """
    cleaned: list[str] = []
    for email in emails:
        if is_blank(email):
            continue
        cleaned.append(email.strip().lower())
    return cleaned

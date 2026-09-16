# Project conventions

- Every module, class and function has a docstring. `ruff` enforces it.
- Every function has complete type annotations. `mypy --strict` enforces it.
- **Cleaning functions never modify what they are given.** They build and return a new
  value. `clean_emails` in `src/cleaner/emails.py` shows the shape.
- Shared string handling lives in `src/cleaner/text.py`. Reuse it rather than writing the
  same check twice.
- Tests live in `tests/`, one file per module, named `test_<module>.py`.

Before finishing a change, run:

    python -m pytest -q
    ruff check .
    mypy src

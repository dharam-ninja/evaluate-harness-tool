# AGENTS.md

Before you finish, run all three of these and make sure they pass:

    python -m pytest -q
    ruff check .
    mypy --strict src

If a check fails, read the error, fix the cause in the source, and run that check again.
Keep going until all three pass.

Do not make a check pass by editing a test, adding `# noqa` for a lint error your own
change introduced, adding `# type: ignore` without justifying it, or loosening a type
annotation.

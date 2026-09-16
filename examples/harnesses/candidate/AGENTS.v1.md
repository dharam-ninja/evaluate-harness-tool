# AGENTS.md

Guidance for agents working in this repository.

## Before you finish

Run all three and make sure they pass:

    python -m pytest -q
    ruff check .
    mypy src

If a check fails, fix the cause rather than the check. Do not edit anything under
`tests/` -- those files define what "done" means.

## Conventions

- Every module, class and public function needs a docstring, and every function needs
  complete type annotations. `ruff` enforces both (`D`, `ANN` rules) and `mypy` runs in
  strict mode.
- Keep imports sorted (`ruff` rule `I001`).
- Prefer the standard library. Do not add dependencies.
- Preserve existing public signatures unless the ticket asks you to change them; other
  modules call them.
- Any flag the `demo` command accepts must appear in the table in `docs/cli.md`.

## Reading a ticket

Tickets state the required behaviour in full. The tests that ship with a ticket cover
the common path and are usually not exhaustive -- implement what the ticket says, not
only what the tests check.

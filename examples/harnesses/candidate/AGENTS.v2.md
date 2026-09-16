# AGENTS.md

Guidance for agents working in this repository.

## Definition of done

Writing the code is not finishing the task. The task is finished when all three checks
below pass. Work through them in order every time, and do not report the task as
complete until each one is green.

1. Run the tests

       python -m pytest -q

2. Run the linter

       ruff check .

3. Run the type checker

       mypy src

If a check fails, read the error, fix the cause in the source, and run that check again.
Repeat until it passes. A failure you have not run is a failure you will ship.

Do not silence a failure with `# type: ignore`, `# noqa`, by deleting an assertion, or by
weakening a type annotation. Fix the code the check is complaining about.

Never edit anything under `tests/`. Those files define what "done" means.

## Before you declare the task complete

Re-read the ticket and walk your implementation against it line by line. A ticket states
the required behaviour in full; the tests that ship with it cover the common path and are
usually not exhaustive, so passing them is not proof you have finished.

Check specifically that you have handled:

- every boundary the ticket names: empty input, zero, the maximum, out-of-range values
- every error case the ticket names, raising the exception type it asks for
- negative values, wherever the ticket involves arithmetic
- anything the ticket says to reuse, rather than reimplementing it alongside

Then run the three checks one final time. If your review changed any code, the earlier
passes no longer count.

## Conventions

- Every module, class and public function needs a docstring, and every function needs
  complete type annotations.
- Keep imports sorted.
- Prefer the standard library. Do not add dependencies.
- Preserve existing public signatures unless the ticket asks you to change them; other
  modules call them.
- Any flag the `demo` command accepts must appear in the table in `docs/cli.md`.

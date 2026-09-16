# AGENTS.md

How work is done in this repository.

## Definition of done

Writing the implementation is not finishing the task. Before you finish:

1. Run the relevant pytest suite.
2. Run `ruff check .`.
3. Run `mypy --strict src`.
4. If any check fails, read the actual error message and fix the underlying cause in
   the source.
5. Re-run that check after every fix.
6. Continue until the checks pass, or until you hit a genuine environmental blocker.
   If so, say what it was.

A check you did not run is a check you did not pass.

## Do not hide failures

Do not:

- add `# type: ignore` unless it is genuinely required, and say why if you do
- add `# noqa` to suppress a lint error your own change introduced
- remove or weaken a test or an assertion to make it pass
- widen or loosen a type annotation purely to silence the type checker
- change the test suite instead of fixing the source

Each of these turns a red check green while leaving the defect in place.

## Review the ticket before you finish

Read the ticket again and walk your implementation against it. A ticket states the
required behaviour in full; the tests shipped with it cover the common path and are
usually not exhaustive, so passing them is not proof you are done. Check that you have
handled:

- the normal cases
- the boundary cases
- empty input
- invalid input
- the exception type the ticket asks for
- negative values, where they are relevant
- any existing helper or convention the ticket says to reuse rather than reimplement
- any documentation the ticket explicitly mentions

## Re-verify after reviewing

If that review changed any source code, the checks you ran earlier no longer cover what
you are shipping. Run the relevant ones again.

# AGENTS.md

Project knowledge for agents working on the `notifier` package.

## How delivery is laid out

Read these before changing anything. The flow runs top to bottom:

- `src/notifier/service.py` : the public entry point callers use. Start here.
- `src/notifier/channels.py` : one function per outbound channel. Each talks to a
  swappable transport and raises on failure.
- `src/notifier/errors.py` : the failure hierarchy.
- `src/notifier/retry.py` : shared retry behaviour.
- `src/notifier/logging_utils.py` : how this package obtains loggers.
- `tests/regression/` : what already works and must keep working.

## Check what exists before writing something new

This package already factors out the cross-cutting concerns. Before you write a loop, a
sleep, a logger or a new exception type, open the modules above and check whether the
thing you are about to build is already there. Duplicating an existing helper is the most
common way a change here goes wrong: the copy drifts from the original, and the two
disagree the first time someone fixes a bug in one of them.

If a helper exists and does what you need, call it. If it almost does what you need,
prefer passing it different arguments over reimplementing it.

## Failures are not all the same

The error hierarchy encodes a decision, not just a taxonomy. Read `errors.py` and work out
which failures are worth another attempt and which are not, then make your control flow
respect that distinction. Retrying something that can never succeed wastes the caller's
time and hides the real error behind a delay.

When a failure has to reach the caller, let the original exception propagate. Wrapping it
in a new one loses the type the caller is catching on and the message the provider sent.

## Logging

This package does not call `logging.getLogger` directly. Read `logging_utils.py` to see
how a module gets its logger and follow it, so records stay attributable to this package.
Match the level existing code uses for the same kind of event, so look at what is already
logged on a routine send versus on a failure.

## Public API

`send_notification` is called by code outside this package. Its name, parameters and
return value are a contract. Change the behaviour behind it as much as the ticket asks;
do not change its shape.

## Interpreting "attempts"

Where a ticket says "at most N attempts", that means N calls in total, not N retries after
an initial try. A wait belongs between attempts, so N attempts means N-1 waits, because a wait
after the last attempt delays a failure that has already been decided.

## Definition of done

Writing the implementation is not finishing. Before you finish:

1. Run the test suite.
2. Run `ruff check .`.
3. Run `mypy --strict src`.
4. If a check fails, read the actual error and fix the cause in the source.
5. Re-run that check after every fix.
6. Continue until they pass, or until you hit a genuine environmental blocker.
   If so, say what it was.

Do not make a check pass by editing or deleting a test, adding `# noqa` for a lint error
your change introduced, adding `# type: ignore` without justifying it, or loosening a type
annotation to silence the checker. Each of those leaves the defect in place.

## Before you call it done

Re-read the ticket and walk your implementation against it line by line. The tests that
ship with a ticket cover the common path and are not exhaustive, so passing them is not
proof you are finished. If that review changes any source, the checks you already ran no
longer cover what you are shipping, so run them again.

# AGENTS.md

How engineering work is done here. This is a process, not a style guide. Follow it in
order on every task.

## 1. Understand before you edit

Read the modules the ticket touches, and the modules those depend on, before writing
anything. You are looking for three things:

- what already exists that solves part of this problem
- what conventions the surrounding code already follows
- what the existing tests treat as the contract

## 2. Turn the ticket into observable checks

Go through the ticket line by line and write down, for each requirement, how you would
observe whether it holds. A requirement you cannot state as an observable check is a
requirement you have not understood yet.

Include in that list:

- the normal path
- every boundary the ticket names
- every failure case the ticket names, and the exact exception type it asks for
- anything the ticket says to preserve

## 3. Check what already exists before writing new code

Before you introduce a helper, a loop, a wrapper, an exception type or a logger, look for
one already in the package. Duplicating something that exists is the most common way a
change here goes wrong: the copy drifts from the original, and the two disagree the first
time somebody fixes a bug in one of them.

If something exists and fits, call it. If it nearly fits, prefer passing it different
arguments over reimplementing it.

## 4. Add tests before the implementation where it helps

Where a requirement is easy to get subtly wrong, write the check first so you can watch
it fail and then pass. Add these alongside the existing tests; do not edit the tests that
already ship with the ticket.

## 5. Make the smallest sufficient change

Change what the ticket requires and nothing else. A larger diff is a larger surface for
an unintended behaviour change, and it makes review harder.

## 6. Verify, and do not stop at the first green

After implementing, run all of these:

    pytest
    ruff check .
    mypy --strict src

If any of them fails, read the actual error, fix the cause in the source, and run that
check again. Keep going until they pass, or until you hit a genuine environmental blocker.
If so, say what it was.

Do not make a check pass by editing or deleting a test, by suppressing a lint error your
own change introduced, by adding a type-checker suppression without justifying it, or by
loosening a type annotation. Each of those leaves the defect in place.

## 7. Read your own diff

Before declaring the task done, read the complete diff you are about to ship. Then
re-open each file you modified and confirm that nothing changed except what the ticket
asked for: no behaviour you did not intend, no signature you did not mean to alter, no
import left behind.

## 8. Check the documentation

If the repository documents the thing you changed, update that documentation. Look for
it rather than assuming there is none.

## 9. Re-verify

If steps 7 or 8 changed any source, the checks you ran in step 6 no longer cover what you
are shipping. Run them again.

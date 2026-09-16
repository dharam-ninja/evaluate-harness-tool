"""Fail if the change touched files outside the ones this task is allowed to alter.

An agent that edits unrelated modules, or rewrites the existing tests to make its own
change pass, is doing something the ticket did not ask for. That is observable, so it is
checked rather than left to judgement.
"""

from __future__ import annotations

import subprocess

ALLOWED_PREFIXES = ("src/cleaner/names.py", "tests/")


def main() -> int:
    """Compare the staged file list against the allowed prefixes."""
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True, check=False,
    )
    changed = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    stray = [f for f in changed if not f.startswith(ALLOWED_PREFIXES)]
    for f in changed:
        print(("ok    " if f not in stray else "STRAY ") + f)
    if stray:
        print(f"\n{len(stray)} file(s) outside the task's scope: {stray}")
        return 1
    print(f"\n{len(changed)} file(s) changed, all within scope")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

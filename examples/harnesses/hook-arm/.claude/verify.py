"""Stop hook: run the project's checks and block completion if any fails.

The agent does not choose whether this runs. That is the whole point of the comparison:
the prose arm is told to run these checks, this arm has them run for it.
"""

from __future__ import annotations

import json
import subprocess
import sys

CHECKS = (
    ("tests", [sys.executable, "-m", "pytest", "-q"]),
    ("lint", [sys.executable, "-m", "ruff", "check", "."]),
    ("types", [sys.executable, "-m", "mypy", "--strict", "src"]),
)


def main() -> int:
    """Run every check; tell the agent to keep working if any of them fail."""
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}
    if payload.get("stop_hook_active"):
        return 0  # already looping on this; let the agent stop

    failures: list[str] = []
    for name, cmd in CHECKS:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            tail = (proc.stdout + proc.stderr).strip()[-1200:]
            failures.append(f"### {name} failed\n{tail}")

    if not failures:
        return 0

    print(json.dumps({
        "decision": "block",
        "reason": (
            "These checks are failing. Fix the cause in the source -- do not edit tests, "
            "add suppressions, or loosen annotations -- then finish.\n\n"
            + "\n\n".join(failures)
        ),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Trial isolation: a genuinely fresh checkout per trial.

Deliberately NOT `git worktree` (PLAN.md §3). Worktrees share the parent's object
store, so trial N could read trial N-1's history -- the cross-trial leakage failure
mode Anthropic's eval guidance flags -- and Claude Code hooks are documented as not
firing reliably inside a linked worktree. A plain copy plus a fresh `git init`
sidesteps both, and needs no symlinks, which matters on Windows.
"""

from __future__ import annotations

import shutil
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .models import AgentHarness, Task

IGNORED = shutil.ignore_patterns(
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "*.pyc"
)

# A fresh repo may have no user identity configured; committing would fail.
_GIT_IDENTITY = [
    "-c", "user.email=harness-eval@localhost",
    "-c", "user.name=harness-eval",
    "-c", "commit.gpgsign=false",
]


def _force_remove(func: Callable[[str], Any], path: str, _exc: Any) -> None:
    """rmtree onerror handler: git writes its object files read-only on Windows."""
    Path(path).chmod(stat.S_IWRITE)
    func(path)


def remove_tree(path: Path) -> None:
    """Delete a workspace, including read-only git objects."""
    shutil.rmtree(path, onerror=_force_remove)


def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *_GIT_IDENTITY, *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


def create_workspace(
    repo: Path, task: Task, dest: Path, harness: AgentHarness | None = None
) -> Path:
    """Copy `repo` to `dest`, overlay the task's visible tests, commit the baseline.

    The acceptance overlay lands BEFORE the initial commit on purpose: the agent may
    read and run those tests, but they must not show up in its patch as work it did.
    """
    if dest.exists():
        remove_tree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo, dest, ignore=IGNORED)

    if (dest / ".git").exists():  # pragma: no cover - defensive
        raise RuntimeError(f"{dest}: .git leaked into the workspace")

    acceptance_dest = dest / "tests" / "acceptance"
    acceptance_dest.mkdir(parents=True, exist_ok=True)
    for src in task.acceptance_tests.iterdir():
        if src.is_file():
            shutil.copy2(src, acceptance_dest / src.name)

    # The harness's instructions are part of the environment under test, not work the
    # agent did. Copying them in AFTER the initial commit made AGENTS.md show up in the
    # candidate's patch and never in the baseline's, so every candidate diff looked
    # larger for a reason that had nothing to do with the agent.
    agents_md = dest / "AGENTS.md"
    if harness is not None and harness.instructions is not None:
        shutil.copy2(harness.instructions, agents_md)
    elif agents_md.exists():
        raise RuntimeError(
            f"{dest}: harness sets instructions: null but AGENTS.md is present -- "
            f"the arms are not distinguishable"
        )

    # Same rule as instructions: configuration is the environment under test, not work
    # the agent did, so it lands before the commit.
    if harness is not None and harness.config_dir is not None:
        for item in harness.config_dir.iterdir():
            target = dest / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

    # The held-out directory must not be reachable from the workspace at any point
    # before grading. Cheap assertion, catches a misconfigured task immediately.
    if (dest / "tests" / "heldout").exists():
        raise RuntimeError(f"{dest}: tests/heldout exists before the agent ran")

    _git(dest, "init", "-q", "-b", "main")
    _git(dest, "add", "-A")
    commit = _git(dest, "commit", "-q", "-m", "initial")
    if commit.returncode != 0:
        raise RuntimeError(f"{dest}: initial commit failed -- {commit.stderr.strip()}")

    log = _git(dest, "log", "--oneline")
    if len(log.stdout.strip().splitlines()) != 1:
        raise RuntimeError(f"{dest}: expected exactly one commit, got:\n{log.stdout}")

    return dest


def changed_files(workspace: Path) -> list[str]:
    """Every path the agent touched, including files it created.

    `git status --porcelain` is read BEFORE staging so untracked files still show as
    `??`. A patch built from `git diff` alone silently drops new files and would
    under-report the agent's work.
    """
    status = _git(workspace, "status", "--porcelain")
    out: list[str] = []
    for line in status.stdout.splitlines():
        if len(line) > 3:
            out.append(line[3:].strip().strip('"'))
    return sorted(out)


def capture_patch(workspace: Path, dest: Path) -> int:
    """Write the agent's full diff to `dest`. Returns the byte count."""
    _git(workspace, "add", "-A")
    diff = _git(workspace, "diff", "--cached")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(diff.stdout, encoding="utf-8")
    return len(diff.stdout.encode("utf-8"))

"""AgentAdapter protocol and the single ShellAgentAdapter implementation.

One shell adapter, not per-product integrations (PLAN.md §0). Anything invokable as a
non-interactive command is a harness, so swapping Claude Code for Codex is a config
change, not a code change.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import AgentHarness, Task


@dataclass
class ShellResult:
    exit_code: int | None
    stdout: str
    stderr: str
    wall_clock_s: float
    timed_out: bool


def _kill_tree(proc: subprocess.Popen[str]) -> None:
    """Kill the process and everything it spawned.

    `Popen.kill()` reaches only the shell. The agent CLI is a grandchild (node), and an
    orphaned one holds the workspace open and corrupts the next trial.
    """
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
    else:  # pragma: no cover - not the target platform
        proc.kill()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:  # pragma: no cover
        pass


def run_shell(
    command: str,
    cwd: Path,
    timeout_s: int,
    stdin_text: str | None = None,
    env: dict[str, str] | None = None,
) -> ShellResult:
    """Run `command` through the shell, killing the whole tree on timeout.

    The evaluator's own interpreter directory goes first on PATH. Without it a grader
    command like `ruff check .` does not resolve at all: it exits 1 with empty output,
    which is indistinguishable from a real lint failure, and the conventions dimension
    reports a confident FAIL for every trial in both arms. It also makes bare `python`
    mean the venv's interpreter rather than whichever one happens to be first on the
    system PATH, so graders and the agent see the same pytest.
    """
    merged = {**os.environ, **(env or {})}
    merged["PATH"] = str(Path(sys.executable).parent) + os.pathsep + merged.get("PATH", "")
    started = time.monotonic()
    proc = subprocess.Popen(
        command,
        cwd=str(cwd),
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=merged,
    )
    try:
        stdout, stderr = proc.communicate(input=stdin_text, timeout=timeout_s)
        return ShellResult(proc.returncode, stdout, stderr, time.monotonic() - started, False)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        stdout, stderr = "", ""
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except Exception:  # noqa: BLE001, S110 - the tree is already dead; draining
            pass          # the pipes is best-effort and must not mask the timeout
        return ShellResult(None, stdout, stderr, time.monotonic() - started, True)


class AgentAdapter(Protocol):
    """The seam that keeps the evaluator decoupled from any one agent product."""

    def run(
        self, task: Task, harness: AgentHarness, workspace: Path, trial_dir: Path, timeout_s: int
    ) -> ShellResult: ...


class ShellAgentAdapter:
    """Runs a configured command per harness."""

    def prepare(self, harness: AgentHarness, workspace: Path) -> None:
        """Apply the harness's project instructions. THIS is the change under test.

        `instructions: null` must mean the file is genuinely absent, not merely
        unwritten -- otherwise the baseline arm silently inherits whatever the repo
        happens to ship and both arms measure the same thing.
        """
        target = workspace / "AGENTS.md"
        if harness.instructions is not None:
            if not target.exists():
                raise RuntimeError(
                    f"{workspace}: harness '{harness.name}' sets instructions but "
                    f"AGENTS.md is absent -- create_workspace did not apply them"
                )
        elif target.exists():
            raise RuntimeError(
                f"{workspace}: harness '{harness.name}' sets instructions: null but "
                f"AGENTS.md is present -- the arms are not distinguishable"
            )

    def run(
        self, task: Task, harness: AgentHarness, workspace: Path, trial_dir: Path, timeout_s: int
    ) -> ShellResult:
        self.prepare(harness, workspace)

        command = harness.command.format(
            prompt="{prompt}", model=harness.model, budget=harness.budget or ""
        ).strip()

        # The prompt goes in on stdin unless the template explicitly interpolates it.
        # Task prompts are multi-line; embedding one in a Windows shell command line is
        # a quoting minefield, and a mangled prompt would look like an agent failure.
        stdin_text: str | None = task.prompt
        if "{prompt}" in command:
            command = command.replace('"{prompt}"', "").replace("{prompt}", "")
            command = " ".join(command.split())

        trial_dir.mkdir(parents=True, exist_ok=True)
        (trial_dir / "command.txt").write_text(command, encoding="utf-8")
        (trial_dir / "prompt.txt").write_text(task.prompt, encoding="utf-8")

        # An endpoint is per-harness, so it must go in the trial's environment rather
        # than the operator's shell -- otherwise the second arm inherits the first's
        # provider and the comparison silently measures one model twice.
        env = dict(harness.env)
        if harness.endpoint:
            env.setdefault("ANTHROPIC_BASE_URL", harness.endpoint)

        result = run_shell(command, workspace, timeout_s, stdin_text, env)

        (trial_dir / "agent_stdout.txt").write_text(result.stdout, encoding="utf-8")
        (trial_dir / "agent_stderr.txt").write_text(result.stderr, encoding="utf-8")
        return result

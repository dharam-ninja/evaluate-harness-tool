"""CommandGrader, the critical flag, and the held-out test overlay.

One generic grader shape, no per-language logic. A grader is a command: exit 0 is a
pass, anything else is a fail. That covers acceptance tests, regression suites, linters
and type-checkers across ecosystems without the evaluator knowing anything about pytest,
ruff or mypy -- and it keeps "add a grader" a YAML-only edit.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .adapters import run_shell
from .evidence import write_result
from .models import Grader, GraderResult, GraderStatus, Task, Trial, TrialStatus

LOG_TAIL_CHARS = 8000


class OverlayVoided(Exception):
    """The overlay destination already existed, so the signal cannot be trusted."""


def _overlay_source(overlay: str, task: Task) -> Path:
    """Resolve `overlay: heldout` to the task's `heldout_tests` directory.

    Looked up by convention rather than hardcoded, so a new overlay kind is a field on
    Task plus a line of YAML, not a branch in here.
    """
    source = getattr(task, f"{overlay}_tests", None)
    if source is None:
        raise ValueError(
            f"grader declares overlay '{overlay}' but task '{task.id}' has no "
            f"'{overlay}_tests' field"
        )
    return Path(source)


def apply_overlay(overlay: str, task: Task, workspace: Path, *, already_applied: bool) -> Path:
    """Copy an overlay's tests into the workspace AFTER the agent has exited.

    The destination must not already exist. If it does, the agent created it -- which
    means it may have seen or guessed the held-out tests, and a pass here would be
    meaningless while a fail would accuse it of a defect nobody demonstrated. Raise, and
    let the caller record the grader as VOID.
    """
    dest = workspace / "tests" / overlay
    if dest.exists() and not already_applied:
        raise OverlayVoided(
            f"{dest} existed before the overlay was applied -- the agent may have seen "
            f"the {overlay} tests, so this trial's {overlay} signal is void"
        )

    dest.mkdir(parents=True, exist_ok=True)
    for src in _overlay_source(overlay, task).iterdir():
        if src.is_file():
            shutil.copy2(src, dest / src.name)
    return dest


def _write_log(path: Path, grader: Grader, result: GraderResult, stdout: str, stderr: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"grader   : {grader.id}",
                f"dimension: {grader.dimension}  critical={grader.critical}",
                f"command  : {grader.command}",
                f"overlay  : {grader.overlay or '-'}",
                f"status   : {result.status.value}",
                f"exit code: {result.exit_code}",
                f"duration : {result.duration_s:.2f}s",
                f"reason   : {result.reason or '-'}",
                "",
                "--- stdout (tail) ---",
                stdout[-LOG_TAIL_CHARS:],
                "",
                "--- stderr (tail) ---",
                stderr[-LOG_TAIL_CHARS:],
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_grader(
    grader: Grader,
    task: Task,
    workspace: Path,
    trial_dir: Path,
    *,
    applied_overlays: set[str] | None = None,
) -> GraderResult:
    """Run one grader in the finished workspace and write its log."""
    applied = applied_overlays if applied_overlays is not None else set()
    log_path = trial_dir / "graders" / f"{grader.id}.log"
    rel_log = f"graders/{grader.id}.log"

    if grader.overlay:
        try:
            apply_overlay(
                grader.overlay, task, workspace, already_applied=grader.overlay in applied
            )
            applied.add(grader.overlay)
        except (OverlayVoided, ValueError) as exc:
            result = GraderResult(
                id=grader.id,
                dimension=grader.dimension,
                critical=grader.critical,
                status=GraderStatus.VOID,
                log_path=rel_log,
                reason=str(exc),
            )
            _write_log(log_path, grader, result, "", str(exc))
            return result

    shell = run_shell(grader.command, workspace, grader.timeout_s)

    if shell.timed_out:
        status = GraderStatus.TIMEOUT
        reason = f"grader exceeded its {grader.timeout_s}s timeout"
    elif shell.exit_code == 0:
        status = GraderStatus.PASS
        reason = None
    else:
        status = GraderStatus.FAIL
        reason = f"exit code {shell.exit_code}"

    result = GraderResult(
        id=grader.id,
        dimension=grader.dimension,
        critical=grader.critical,
        status=status,
        exit_code=shell.exit_code,
        duration_s=round(shell.wall_clock_s, 2),
        log_path=rel_log,
        reason=reason,
    )
    _write_log(log_path, grader, result, shell.stdout, shell.stderr)
    return result


def grade_trial(
    trial: Trial, graders: list[Grader], task: Task, workspace: Path, trial_dir: Path
) -> Trial:
    """Run every grader against a finished trial and record the results.

    Called only after `evidence.collect` has taken patch.diff. If an overlay landed
    first, the patch would contain tests the agent never wrote and the diff would
    overstate its work.
    """
    if trial.status is TrialStatus.ERROR:
        return trial

    applied: set[str] = set()
    trial.graders = [
        run_grader(g, task, workspace, trial_dir, applied_overlays=applied) for g in graders
    ]
    write_result(trial_dir, trial)
    return trial

"""CommandGrader exit-code mapping, timeouts, and the held-out overlay.

Every assertion matches the failure *reason*, not just the status. A test that only
checks `status is FAIL` passes whether the command failed, timed out, or the overlay
was voided -- three things the report must keep apart (NOTES.md T+2:20).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from harness_eval.adapters import run_shell
from harness_eval.config import load_config
from harness_eval.graders import OverlayVoided, apply_overlay, grade_trial, run_grader
from harness_eval.models import Grader, GraderStatus, Task, Trial, TrialStatus
from harness_eval.workspace import create_workspace

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "examples" / "eval.yaml"
PY = Path(sys.executable).as_posix()


@pytest.fixture
def task() -> Task:
    return load_config(EXAMPLE).tasks[0]


@pytest.fixture
def workspace(tmp_path: Path, task: Task) -> Path:
    """A fresh trial workspace, exactly as the runner builds one."""
    cfg = load_config(EXAMPLE)
    return create_workspace(cfg.repo, task, tmp_path / "ws")


def _grader(command: str, **kw: object) -> Grader:
    defaults = {"id": "probe", "command": command, "dimension": "correctness", "critical": True}
    return Grader(**{**defaults, **kw})  # type: ignore[arg-type]


# --------------------------------------------------------------------- exit-code mapping


def test_exit_zero_is_a_pass(workspace: Path, task: Task, tmp_path: Path) -> None:
    res = run_grader(_grader(f'{PY} -c "raise SystemExit(0)"'), task, workspace, tmp_path)
    assert res.status is GraderStatus.PASS
    assert res.exit_code == 0
    assert res.reason is None


def test_nonzero_exit_is_a_fail_carrying_the_code(
    workspace: Path, task: Task, tmp_path: Path
) -> None:
    res = run_grader(_grader(f'{PY} -c "raise SystemExit(3)"'), task, workspace, tmp_path)
    assert res.status is GraderStatus.FAIL
    assert res.exit_code == 3
    assert "exit code 3" in (res.reason or "")


def test_grader_writes_a_log_with_the_command_and_output(
    workspace: Path, task: Task, tmp_path: Path
) -> None:
    res = run_grader(_grader(f'{PY} -c "print(\'hello-from-grader\')"'), task, workspace, tmp_path)
    log = (tmp_path / (res.log_path or "")).read_text(encoding="utf-8")
    assert "hello-from-grader" in log
    assert "command  :" in log
    assert "status   : pass" in log


# ------------------------------------------------------------------------------ timeouts


def test_timeout_is_distinct_from_failure_and_does_not_crash(
    workspace: Path, task: Task, tmp_path: Path
) -> None:
    """A slow grader must not be indistinguishable from a failing one."""
    slow = _grader(f'{PY} -c "import time; time.sleep(30)"', timeout_s=2)
    res = run_grader(slow, task, workspace, tmp_path)
    assert res.status is GraderStatus.TIMEOUT
    assert res.status is not GraderStatus.FAIL
    assert "timeout" in (res.reason or "").lower()


def test_run_shell_kills_the_whole_process_tree(tmp_path: Path) -> None:
    """Phase 3's taskkill path. An orphaned grandchild would hold the workspace open."""
    spawner = tmp_path / "spawn.py"
    spawner.write_text(
        "import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
        "time.sleep(120)\n",
        encoding="utf-8",
    )
    res = run_shell(f'{PY} "{spawner.as_posix()}"', tmp_path, timeout_s=3)
    assert res.timed_out is True
    assert res.exit_code is None
    assert res.wall_clock_s < 30  # returned promptly rather than waiting out the child


# ------------------------------------------------------------------------------- overlay


def test_overlay_lands_in_the_workspace(workspace: Path, task: Task) -> None:
    assert not (workspace / "tests" / "heldout").exists()
    dest = apply_overlay("heldout", task, workspace, already_applied=False)
    copied = sorted(p.name for p in dest.glob("*.py"))
    expected = sorted(p.name for p in task.heldout_tests.glob("*.py"))
    assert copied == expected and copied


def test_a_fresh_workspace_never_contains_the_heldout_tests(workspace: Path) -> None:
    """The overlay must be the only way those tests can reach a workspace."""
    assert not (workspace / "tests" / "heldout").exists()
    names = {p.name for p in workspace.rglob("*.py")}
    assert "test_rounding_heldout.py" not in names


def test_overlay_is_voided_when_the_destination_already_exists(
    workspace: Path, task: Task
) -> None:
    """If the agent created tests/heldout, it may have seen the tests."""
    (workspace / "tests" / "heldout").mkdir(parents=True)
    with pytest.raises(OverlayVoided, match="void"):
        apply_overlay("heldout", task, workspace, already_applied=False)


def test_voided_overlay_grades_as_VOID_not_PASS_or_FAIL(
    workspace: Path, task: Task, tmp_path: Path
) -> None:
    (workspace / "tests" / "heldout").mkdir(parents=True)
    res = run_grader(
        _grader(f'{PY} -c "raise SystemExit(0)"', overlay="heldout"), task, workspace, tmp_path
    )
    assert res.status is GraderStatus.VOID
    assert res.status not in (GraderStatus.PASS, GraderStatus.FAIL)
    assert "may have seen" in (res.reason or "")


def test_a_void_critical_grader_makes_the_trial_unmeasurable(
    workspace: Path, task: Task, tmp_path: Path
) -> None:
    (workspace / "tests" / "heldout").mkdir(parents=True)
    trial = Trial(task_id=task.id, harness="baseline", rep=0, status=TrialStatus.COMPLETED)
    graded = grade_trial(
        trial,
        [_grader(f'{PY} -c "raise SystemExit(0)"', overlay="heldout")],
        task,
        workspace,
        tmp_path,
    )
    assert graded.measurable is False
    assert graded.critical_pass is False


def test_a_second_grader_sharing_an_overlay_does_not_void_itself(
    workspace: Path, task: Task, tmp_path: Path
) -> None:
    """Two graders may both declare overlay: heldout. The second must not self-trip."""
    graders = [
        _grader(f'{PY} -c "raise SystemExit(0)"', id="first", overlay="heldout"),
        _grader(f'{PY} -c "raise SystemExit(0)"', id="second", overlay="heldout"),
    ]
    trial = Trial(task_id=task.id, harness="baseline", rep=0, status=TrialStatus.COMPLETED)
    graded = grade_trial(trial, graders, task, workspace, tmp_path)
    assert [g.status for g in graded.graders] == [GraderStatus.PASS, GraderStatus.PASS]


def test_unknown_overlay_name_is_voided_with_a_clear_reason(
    workspace: Path, task: Task, tmp_path: Path
) -> None:
    res = run_grader(
        _grader(f'{PY} -c "raise SystemExit(0)"', overlay="nosuch"), task, workspace, tmp_path
    )
    assert res.status is GraderStatus.VOID
    assert "nosuch_tests" in (res.reason or "")


# ------------------------------------------------------------------------- real graders


def test_the_real_graders_run_against_an_ungraded_workspace(
    workspace: Path, task: Task, tmp_path: Path
) -> None:
    """End to end on the actual config: the demo repo starts failing the task."""
    cfg = load_config(EXAMPLE)
    trial = Trial(task_id=task.id, harness="baseline", rep=0, status=TrialStatus.COMPLETED)
    graded = grade_trial(trial, cfg.graders, task, workspace, tmp_path)

    by_id = {g.id: g for g in graded.graders}
    assert len(graded.graders) == len(cfg.graders)
    # Unmodified repo: the task is genuinely unsolved, the pre-existing suite is clean.
    assert by_id["acceptance"].status is GraderStatus.FAIL
    assert by_id["heldout"].status is GraderStatus.FAIL
    assert by_id["regressions"].status is GraderStatus.PASS
    assert by_id["lint"].status is GraderStatus.PASS
    assert graded.measurable is True
    for g in graded.graders:
        assert (tmp_path / (g.log_path or "")).is_file()


def test_errored_trials_are_not_graded(task: Task, tmp_path: Path) -> None:
    """There is no workspace to grade, and a fabricated FAIL would be a false defect."""
    trial = Trial(task_id=task.id, harness="baseline", rep=0, status=TrialStatus.ERROR)
    graded = grade_trial(trial, [_grader("true")], task, tmp_path / "gone", tmp_path)
    assert graded.graders == []
    assert graded.measurable is False

"""Report renders from fixture artifacts and every claim links to evidence.

The link checks are the point. An aggregate number whose link 404s is worse than no link:
it looks auditable and is not.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from harness_eval.comparator import build_report
from harness_eval.models import GraderResult, GraderStatus, Trial, TrialStatus
from harness_eval.report import invariant_graders, render


def _trial(
    task: str, arm: str, rep: int, *, passing: bool = True, lint: bool = True,
    cost: float | None = 1.0, status: TrialStatus = TrialStatus.COMPLETED,
) -> Trial:
    t = Trial(
        task_id=task, harness=arm, rep=rep, status=status, wall_clock_s=10.0,
        files_changed=["src/demo/money.py"],
        graders=[
            GraderResult(id="acceptance", dimension="correctness", critical=True,
                         status=GraderStatus.PASS if passing else GraderStatus.FAIL,
                         log_path="graders/acceptance.log"),
            GraderResult(id="heldout", dimension="fidelity", critical=True,
                         status=GraderStatus.PASS if passing else GraderStatus.FAIL,
                         log_path="graders/heldout.log"),
            GraderResult(id="lint", dimension="conventions", critical=False,
                         status=GraderStatus.PASS if lint else GraderStatus.FAIL,
                         log_path="graders/lint.log"),
        ],
    )
    t.usage.total_cost_usd = cost
    return t


def _run(tmp_path: Path, trials: list[Trial], **kw: Any) -> Path:
    """Write a run directory whose artifacts actually exist on disk."""
    manifest = {
        "run_id": "fixture", "created_utc": "2026-09-15T00:00:00+00:00",
        "config": "examples/eval.yaml", "reps": 2, "jobs": 1,
        "schedule": "counterbalanced-task-rep",
        "dimensions": ["correctness", "fidelity", "conventions"],
        "tasks": sorted({t.task_id for t in trials}),
        "graders": [
            {"id": "acceptance", "command": "x", "dimension": "correctness", "critical": True},
            {"id": "heldout", "command": "y", "dimension": "fidelity", "critical": True},
            {"id": "lint", "command": "z", "dimension": "conventions", "critical": False},
        ],
        "trials": [t.model_dump(mode="json") for t in trials],
    }
    manifest.update(kw)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for t in trials:
        d = tmp_path / "trials" / t.task_id / t.harness / str(t.rep)
        (d / "graders").mkdir(parents=True, exist_ok=True)
        for name in ("patch.diff", "transcript.json", "prompt.txt", "command.txt"):
            (d / name).write_text("fixture", encoding="utf-8")
        for g in t.graders:
            (d / "graders" / f"{g.id}.log").write_text("fixture", encoding="utf-8")
    return tmp_path


def _links(md: Path) -> list[tuple[str, str]]:
    return re.findall(r"\[([^\]]+)\]\(([^)]+)\)", md.read_text(encoding="utf-8"))


@pytest.fixture
def rendered(tmp_path: Path) -> Path:
    trials = [
        _trial("t1", arm, rep) for arm in ("baseline", "candidate") for rep in (0, 1)
    ] + [
        _trial("t2", "baseline", rep, passing=False) for rep in (0, 1)
    ] + [
        _trial("t2", "candidate", rep, passing=True, lint=False) for rep in (0, 1)
    ]
    run = _run(tmp_path, trials)
    render(run)
    return run


# ------------------------------------------------------------------------------- links


def test_every_link_in_every_rendered_page_resolves(rendered: Path) -> None:
    """An aggregate number whose link 404s looks auditable and is not."""
    pages = [rendered / "report.md", *sorted((rendered / "tasks").glob("*.md"))]
    broken = [
        (page.name, href)
        for page in pages
        for _, href in _links(page)
        if not (page.parent / href).resolve().exists()
    ]
    assert broken == []


def test_task_pages_climb_out_of_their_own_directory(rendered: Path) -> None:
    """tasks/<id>.md is one level down; artifact links must start with ../"""
    for page in (rendered / "tasks").glob("*.md"):
        for _, href in _links(page):
            if "trials/" in href:
                assert href.startswith("../"), f"{page.name}: {href}"


def test_report_json_evidence_paths_resolve(rendered: Path) -> None:
    data = json.loads((rendered / "report.json").read_text(encoding="utf-8"))
    for ev in data["evidence"].values():
        assert (rendered / ev["page"]).exists()
        for trials in ev["trials"].values():
            for t in trials:
                assert (rendered / t["patch"]).exists()
                for g in t["graders"].values():
                    assert (rendered / g["log"]).exists()


# ------------------------------------------------------------------------------ content


def test_the_printed_rule_matches_the_rule_the_code_ran(rendered: Path) -> None:
    from harness_eval.comparator import RULES

    body = (rendered / "report.md").read_text(encoding="utf-8")
    report = build_report(rendered)
    assert report.rule_fired in body
    for rule in RULES:
        assert rule.name in body, f"{rule.name} missing from the printed rule"


def test_report_json_carries_the_inputs_needed_to_recompute_the_verdict(rendered: Path) -> None:
    data = json.loads((rendered / "report.json").read_text(encoding="utf-8"))
    inputs = data["rule"]["inputs"]
    assert set(inputs) >= {
        "improvements", "regressions", "unstable", "unmeasured",
        "baseline_passes", "candidate_passes", "cost_delta_pct", "reps",
    }
    assert data["rule"]["ordered_conditions"]


def test_cost_figures_never_appear_without_their_qualifier(rendered: Path) -> None:
    """The number and the reason it needs qualifying must travel together.

    Every dollar figure is qualified where it is printed, not only in a caveat further
    down: a mean says "per successful trial", a total says it covers all trials. The
    section takes one of two shapes -- a valid comparison, or a withheld one -- and both
    must carry their qualifier.
    """
    body = (rendered / "report.md").read_text(encoding="utf-8")
    cost_section = body.split("\nCost\n")[1].split("=" * 32)[0]

    comparable = "per successful trial" in cost_section
    withheld = "NOT COMPARABLE" in cost_section
    assert comparable != withheld, "the section must be exactly one of the two shapes"

    if comparable:
        # A raw total printed beside a mean is the easiest figure in the report to misread.
        assert "all trials, successful or not" in cost_section
    else:
        assert "passed 0 of" in cost_section  # the withheld case must say why

    assert "Successful trials only" in cost_section
    assert "Paired by task" in cost_section


def test_the_business_fidelity_checklist_is_empty_for_a_human_to_fill_in(
    rendered: Path,
) -> None:
    body = (rendered / "report.md").read_text(encoding="utf-8")
    section = body.split("Business Fidelity")[1]
    assert "[ ]" in section
    assert "[x]" not in section  # nothing pre-answered


def test_confidence_is_never_reported_as_high(rendered: Path) -> None:
    assert "HIGH confidence" not in (rendered / "report.md").read_text(encoding="utf-8")


def test_a_divergent_trial_is_called_out_on_its_task_page(tmp_path: Path) -> None:
    t = _trial("t1", "candidate", 0)
    t.graders[1].status = GraderStatus.FAIL  # acceptance pass, heldout fail
    run = _run(tmp_path, [t, _trial("t1", "baseline", 0)], reps=1)
    render(run)
    page = (run / "tasks" / "t1.md").read_text(encoding="utf-8")
    assert "A green suite did not mean correct behaviour" in page


# ------------------------------------------------------------------- invariant graders


def test_a_grader_that_never_varies_between_arms_is_flagged(tmp_path: Path) -> None:
    """It measured the task, not the harness -- it cancels out of every delta."""
    trials = [_trial("t1", arm, rep) for arm in ("baseline", "candidate") for rep in (0, 1)]
    for t in trials:
        t.graders[2].status = GraderStatus.FAIL  # lint fails everywhere
    run = _run(tmp_path, trials)
    render(run)
    flagged = invariant_graders(build_report(run))
    assert {"task": "t1", "grader": "lint", "verdict": "fail"} in flagged
    assert "Graders That Never Varied" in (run / "report.md").read_text(encoding="utf-8")


def test_a_grader_passing_everywhere_is_not_flagged_as_a_defect(tmp_path: Path) -> None:
    trials = [_trial("t1", arm, rep) for arm in ("baseline", "candidate") for rep in (0, 1)]
    run = _run(tmp_path, trials)
    assert invariant_graders(build_report(run)) == []


# -------------------------------------------------------------------------- robustness


def test_renders_from_a_partial_run_without_crashing(tmp_path: Path) -> None:
    """Iterating on the report happens while trials are still landing."""
    run = _run(tmp_path, [_trial("t1", "baseline", 0)], reps=2)
    render(run)
    assert (run / "report.md").exists()
    assert "UNMEASURED" in (run / "report.md").read_text(encoding="utf-8")


def test_renders_an_empty_run_without_crashing(tmp_path: Path) -> None:
    run = _run(tmp_path, [])
    render(run)
    assert (run / "report.md").exists()


def test_a_concurrent_run_gets_a_wall_clock_warning_banner(tmp_path: Path) -> None:
    run = _run(tmp_path, [_trial("t1", "baseline", 0)], jobs=4)
    render(run)
    body = (run / "report.md").read_text(encoding="utf-8")
    assert "Trials ran concurrently" in body
    assert "jobs=4" in body


def test_an_uncounterbalanced_run_says_so_next_to_the_cost_number(tmp_path: Path) -> None:
    """full-01 predates the fix; its cost delta must not read as a clean measurement."""
    trials = [_trial("t1", arm, rep) for arm in ("baseline", "candidate") for rep in (0, 1)]
    run = _run(tmp_path, trials, schedule=None)
    render(run)
    body = (run / "report.md").read_text(encoding="utf-8")
    assert "predates arm-order counterbalancing" in body

"""Jinja2 rendering to report.md, report.json, and per-task pages.

Rendering only. Every number comes from the EvaluationReport the comparator built, and the
recommendation rule is printed from `comparator.RULES` rather than restated here, so the
report cannot describe a policy the code does not run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .comparator import build_report
from .models import EvaluationReport, GraderStatus, Outcome, TaskComparison, Transition, Trial

TEMPLATES = Path(__file__).parent / "templates"

#: Rendered next to each transition so the table reads without a legend.
TRANSITION_LABEL = {
    Transition.IMPROVED: "**IMPROVED**",
    Transition.REGRESSED: "**REGRESSION**",
    Transition.UNCHANGED_PASS: "unchanged (both pass)",
    Transition.UNCHANGED_FAIL: "unchanged (both fail)",
    Transition.UNSTABLE: "UNSTABLE - excluded from counts",
    Transition.UNMEASURED: "UNMEASURED - excluded from counts",
}

STATUS_MARK = {
    GraderStatus.PASS: "pass",
    GraderStatus.FAIL: "FAIL",
    GraderStatus.TIMEOUT: "TIMEOUT",
    GraderStatus.VOID: "VOID",
}


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["money"] = lambda v: "n/a" if v is None else f"${v:.4f}"
    env.filters["pct"] = lambda v: "n/a" if v is None else f"{v:+.1f}%"
    env.filters["secs"] = lambda v: "n/a" if v is None else f"{v:.1f}s"
    return env


def invariant_graders(report: EvaluationReport) -> list[dict[str, Any]]:
    """Graders that returned the same verdict in every trial of BOTH arms.

    Such a grader measured the task, not the evaluand. `add-retry`/`types` failed 4/4 in
    both arms because the natural implementation of that ticket cannot satisfy mypy
    strict (NOTES.md T+5:00). Folding that silently into a dimension makes both harnesses
    look worse than the evidence supports, so it is called out instead.
    """
    seen: dict[tuple[str, str], set[str]] = {}
    for comp in report.comparisons:
        for trials in comp.trials.values():
            for trial in trials:
                for g in trial.graders:
                    seen.setdefault((comp.task_id, g.id), set()).add(g.status.value)
    out = []
    for (task_id, grader_id), statuses in sorted(seen.items()):
        if len(statuses) == 1 and statuses != {GraderStatus.PASS.value}:
            out.append({"task": task_id, "grader": grader_id, "verdict": statuses.pop()})
    return out


def dimension_evidence(report: EvaluationReport) -> dict[str, list[dict[str, Any]]]:
    """Per-grader trial counts behind each dimension score.

    The dimension row says 3/4 tasks. This says which grader produced that and how many
    individual trials it passed in each arm, so the headline number has a countable
    thing underneath it rather than a rollup of a rollup.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    for dim in report.dimensions:
        rows = []
        for grader_id in dim.graders:
            counts = {"baseline": [0, 0], "candidate": [0, 0]}
            example: str | None = None
            for comp in report.comparisons:
                for arm, trials in comp.trials.items():
                    if arm not in counts:
                        continue
                    for t in trials:
                        g = t.grader(grader_id)
                        if g is None:
                            continue
                        counts[arm][1] += 1
                        if g.status is GraderStatus.PASS:
                            counts[arm][0] += 1
                        elif example is None and g.log_path:
                            example = trial_link(t, g.log_path)
            rows.append({
                "grader": grader_id,
                "baseline": counts["baseline"],
                "candidate": counts["candidate"],
                "example_failure_log": example,
            })
        out[dim.dimension] = rows
    return out


def trial_link(trial: Trial, filename: str = "") -> str:
    """Relative path from the report to a trial artifact."""
    base = f"trials/{trial.task_id}/{trial.harness}/{trial.rep}"
    return f"{base}/{filename}" if filename else base


def task_link(task_id: str) -> str:
    return f"tasks/{task_id}.md"


def _task_context(comp: TaskComparison) -> dict[str, Any]:
    # Task pages sit one directory below the run root, so every artifact link needs to
    # climb out of tasks/ first. Without this the links render fine and 404 on click.
    def up(trial: Trial, filename: str = "") -> str:
        return "../" + trial_link(trial, filename)

    return {
        "c": comp,
        "label": TRANSITION_LABEL[comp.transition],
        "mark": STATUS_MARK,
        "trial_link": up,
        "Outcome": Outcome,
        "GraderStatus": GraderStatus,
    }


def render(run_dir: Path, report: EvaluationReport | None = None) -> EvaluationReport:
    """Write report.md, report.json and tasks/<task>.md into `run_dir`."""
    report = report or build_report(run_dir)
    env = _env()

    context: dict[str, Any] = {
        "r": report,
        "label": TRANSITION_LABEL,
        "mark": STATUS_MARK,
        "task_link": task_link,
        "trial_link": trial_link,
        "invariant": invariant_graders(report),
        "evidence": dimension_evidence(report),
        "Transition": Transition,
        "Outcome": Outcome,
        "GraderStatus": GraderStatus,
    }

    (run_dir / "report.md").write_text(
        env.get_template("report.md.j2").render(**context), encoding="utf-8"
    )

    tasks_dir = run_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    task_tpl = env.get_template("task.md.j2")
    for comp in report.comparisons:
        (tasks_dir / f"{comp.task_id}.md").write_text(
            task_tpl.render(**_task_context(comp)), encoding="utf-8"
        )

    (run_dir / "report.json").write_text(
        json.dumps(as_json(report), indent=2), encoding="utf-8"
    )
    return report


def as_json(report: EvaluationReport) -> dict[str, Any]:
    """Machine-readable form. A consumer can recompute the recommendation from this.

    The rule is emitted alongside the inputs it was evaluated against, so the verdict is
    reproducible from the file rather than something the reader has to take on trust.
    """
    data = report.model_dump(mode="json")
    data["rule"] = {
        "fired": report.rule_fired,
        "ordered_conditions": report.rule_text,
        "inputs": {
            "improvements": len(report.improvements),
            "regressions": len(report.regressions),
            "unstable": len(report.unstable),
            "unmeasured": len(report.unmeasured),
            "baseline_passes": sum(
                1 for c in report.comparisons
                if c.is_counted and c.outcomes["baseline"] is Outcome.PASS
            ),
            "candidate_passes": sum(
                1 for c in report.comparisons
                if c.is_counted and c.outcomes["candidate"] is Outcome.PASS
            ),
            "cost_delta_pct": report.cost.delta_pct,
            "reps": report.reps,
        },
    }
    data["evidence"] = {
        c.task_id: {
            "page": task_link(c.task_id),
            "trials": {
                arm: [
                    {
                        "rep": t.rep,
                        "status": t.status.value,
                        "patch": trial_link(t, "patch.diff"),
                        "transcript": trial_link(t, "transcript.json"),
                        "graders": {
                            g.id: {"status": g.status.value, "log": trial_link(t, g.log_path or "")}
                            for g in t.graders
                        },
                    }
                    for t in trials
                ]
                for arm, trials in c.trials.items()
            },
        }
        for c in report.comparisons
    }
    data["invariant_graders"] = invariant_graders(report)
    data["dimension_evidence"] = dimension_evidence(report)
    return data

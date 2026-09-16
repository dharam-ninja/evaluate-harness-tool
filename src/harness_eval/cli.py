"""Typer CLI: validate | run | report | evaluate.

`run` and `report` are separate on purpose (PLAN.md §4). Trials are expensive and
non-deterministic; rendering is neither. Every report fix re-renders from runs/ in
seconds instead of re-spending an hour and real money.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from .adapters import ShellAgentAdapter
from .config import ConfigError, load_config
from .evidence import collect
from .graders import grade_trial
from .models import AgentHarness, EvalConfig, Trial, TrialStatus
from .report import render
from .workspace import create_workspace

app = typer.Typer(add_completion=False, help="Paired baseline-vs-candidate evaluation for coding-agent harnesses.")
console = Console()

_STATUS_STYLE = {
    TrialStatus.COMPLETED: "green",
    TrialStatus.TIMEOUT: "yellow",
    TrialStatus.BLOCKED: "magenta",
    TrialStatus.ERROR: "red",
}


def _load(path: Path) -> EvalConfig:
    try:
        return load_config(path)
    except ConfigError as exc:
        console.print(f"[red]config error[/red] {exc}")
        raise typer.Exit(2) from exc


@app.command()
def validate(config: Path = typer.Argument(..., help="Path to eval.yaml")) -> None:
    """Parse the config and print what would run. Runs nothing."""
    cfg = _load(config)
    total = len(cfg.tasks) * len(cfg.harnesses) * cfg.reps
    console.print(f"[bold]{cfg.source}[/bold]")
    console.print(f"  repo      {cfg.repo}")
    for name, h in cfg.harnesses.items():
        instr = h.instructions.name if h.instructions else "[dim]none[/dim]"
        console.print(
            f"  harness   {name:<10} model={h.model}  provider={h.provider}  instructions={instr}"
        )
    console.print(f"  tasks     {', '.join(t.id for t in cfg.tasks)}")
    console.print(f"  graders   {', '.join(g.id + ('*' if g.critical else '') for g in cfg.graders)}  [dim](* = critical)[/dim]")
    console.print(f"  variable  {', '.join(cfg.intended_difference)}  [dim](everything else must match)[/dim]")
    console.print(
        f"\n[bold]{len(cfg.tasks)} tasks x {len(cfg.harnesses)} harnesses x {cfg.reps} reps = {total} trials[/bold]"
    )
    if cfg.jobs > 1:
        console.print(f"[yellow]jobs={cfg.jobs}: wall-clock figures will be unreliable[/yellow]")


def _execute(
    cfg: EvalConfig, out: Path, rid: str, only_task: str, only_harness: str, n_reps: int
) -> Path:
    """Run every trial in the plan and write the run directory. Renders nothing."""
    run_dir = (out / rid).resolve()
    (run_dir / "trials").mkdir(parents=True, exist_ok=True)

    tasks = [t for t in cfg.tasks if not only_task or t.id == only_task]
    harnesses = {k: v for k, v in cfg.harnesses.items() if not only_harness or k == only_harness}
    if not tasks:
        console.print(f"[red]no task matching '{only_task}'[/red]")
        raise typer.Exit(2)

    adapter = ShellAgentAdapter()
    results: list[Trial] = []
    total = len(tasks) * len(harnesses) * n_reps
    started = time.monotonic()
    console.print(f"[bold]run {rid}[/bold]  {total} trials -> {run_dir}\n")

    for task_index, t in enumerate(tasks):
        for rep in range(n_reps):
            order = list(harnesses)
            # Counterbalanced on (task, rep), not rep alone. Alternating by rep only
            # produces b,c,c,b for every task, which leaves the baseline in execution
            # position 1 -- the cold-cache slot -- every single time. Measured on
            # full-01: position 1 costs +17.2% over positions 2-4, handing the candidate
            # a 10% cost advantage from scheduling alone (NOTES.md T+5:00, finding 4).
            if (task_index + rep) % 2:
                order.reverse()
            for hname in order:
                h = harnesses[hname]
                trial_dir = run_dir / "trials" / t.id / hname / str(rep)
                ws = run_dir / "workspaces" / t.id / hname / str(rep)
                console.print(f"  [dim]running[/dim] {t.id}/{hname}/{rep} ...")
                try:
                    create_workspace(cfg.repo, t, ws, h)
                    shell = adapter.run(t, h, ws, trial_dir, cfg.timeout_s)
                    res = collect(t.id, hname, rep, ws, trial_dir, shell)
                    # strictly after collect(): the overlay must not reach the patch
                    res = grade_trial(res, cfg.graders, t, ws, trial_dir)
                except Exception as exc:  # noqa: BLE001 - one broken trial must not
                    # abort a run that costs money; it is recorded as an ERROR trial instead
                    res = Trial(
                        task_id=t.id, harness=hname, rep=rep,
                        status=TrialStatus.ERROR, error=f"{type(exc).__name__}: {exc}",
                        trial_dir=str(trial_dir),
                    )
                    trial_dir.mkdir(parents=True, exist_ok=True)
                    (trial_dir / "result.json").write_text(res.model_dump_json(indent=2), encoding="utf-8")
                results.append(res)
                console.print(f"    {_summarise(res)}")

    # Recorded with the run, not asserted in prose: which harness fields were identical
    # and which one was intended to differ. A reader can audit the control from the
    # manifest alone, without re-reading the config that produced it.
    fairness: dict[str, Any] = {}
    if {"baseline", "candidate"} <= set(harnesses):
        b, c = harnesses["baseline"], harnesses["candidate"]
        controlled_fields = [
            f for f in ("command", "model", "endpoint", "budget", "env", "instructions", "config_dir")
            if f not in cfg.intended_difference
        ]
        fairness = {
            "intended_difference": cfg.intended_difference,
            "identical": {
                field: getattr(b, field) == getattr(c, field) for field in controlled_fields
            },
            "differs_as_intended": {
                field: {"baseline": _shown(getattr(b, field)),
                        "candidate": _shown(getattr(c, field))}
                for field in cfg.intended_difference
            },
            "models": {
                "baseline": {"model": b.model, "provider": b.provider},
                "candidate": {"model": c.model, "provider": c.provider},
            },
        }
        # Controlled means: everything not declared as the variable is identical, AND
        # every field declared as the variable actually differs. A "difference" that is
        # the same on both sides is a config mistake, not an experiment.
        fairness["controlled"] = all(fairness["identical"].values()) and all(
            getattr(b, f) != getattr(c, f) for f in cfg.intended_difference
        )

    manifest = {
        "run_id": rid,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(cfg.source),
        "repo": str(cfg.repo),
        "change": cfg.change,
        "reps": n_reps,
        "jobs": cfg.jobs,
        "schedule": "counterbalanced-task-rep",
        "fairness": fairness,
        "dimensions": cfg.dimensions,
        "harnesses": {k: _harness_dump(v) for k, v in harnesses.items()},
        "tasks": [t.id for t in tasks],
        "graders": [g.model_dump(mode="json") for g in cfg.graders],
        "trials": [r.model_dump(mode="json") for r in results],
        "wall_clock_s": round(time.monotonic() - started, 1),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    spend = sum(r.usage.total_cost_usd or 0.0 for r in results)
    console.print(
        f"\n[bold]done[/bold]  {len(results)} trials in {manifest['wall_clock_s']}s  "
        f"total ${spend:.2f}\n  {run_dir / 'manifest.json'}"
    )
    return run_dir


REDACTED = "<redacted>"


def _redact_env(env: dict[str, Any]) -> dict[str, str]:
    """Keep the variable names, drop every value.

    A harness `env` block is where credentials are passed -- the README documents
    ANTHROPIC_AUTH_TOKEN there -- and `${VAR}` is expanded at config-load time, so by the
    time a harness reaches this module the plaintext secret is in this dict. The manifest
    lands in a run directory that .gitignore re-includes by name for demonstration
    samples, so anything recorded here can be committed and pushed.

    Names are kept because they are what makes a run reproducible: the config records
    which `${VAR}` fills each one, and the reader sets that variable themselves.
    """
    return {key: REDACTED for key in env}


def _harness_dump(harness: AgentHarness) -> dict[str, Any]:
    """The manifest's record of one harness, with env values redacted."""
    dumped: dict[str, Any] = harness.model_dump(mode="json")
    dumped["env"] = _redact_env(dumped.get("env") or {})
    return dumped


def _shown(value: Any) -> Any:
    """Render a harness field for the manifest without leaking a secret."""
    if isinstance(value, dict):  # only `env` is a dict, and only it can hold a credential
        return _redact_env(value)
    return str(value) if isinstance(value, Path) else value


def _summarise(res: Trial) -> str:
    cost = res.usage.total_cost_usd
    cost_s = f"${cost:.4f}" if cost is not None else "[dim]cost n/a[/dim]"
    graders = " ".join(
        f"[green]{g.id}[/green]" if g.passed else f"[red]{g.id}[/red]" for g in res.graders
    )
    return (
        f"[{_STATUS_STYLE[res.status]}]{res.status.value:<9}[/] "
        f"{res.wall_clock_s:>6.1f}s  {cost_s}  "
        f"{len(res.files_changed)} file(s)  {res.patch_bytes}B  {graders}"
    )


def _render(run_dir: Path) -> None:
    """Render report.md + report.json from an existing run directory."""
    report = render(run_dir)
    console.print(
        f"\n[bold]{report.recommendation.value}[/bold] - {report.confidence.value} confidence "
        f"[dim](rule: {report.rule_fired})[/dim]"
    )
    console.print(
        f"  {len(report.improvements)} improved, {len(report.regressions)} regressed, "
        f"{len(report.unstable)} unstable, {len(report.unmeasured)} unmeasured"
    )
    console.print(f"\n  {run_dir / 'report.md'}\n  {run_dir / 'report.json'}")


@app.command()
def run(
    config: Path = typer.Argument(..., help="Path to eval.yaml"),
    out: Path = typer.Option(Path("runs"), help="Directory to write run artifacts into"),
    run_id: str = typer.Option("", help="Override the generated run id"),
    task: str = typer.Option("", help="Run only this task id"),
    harness: str = typer.Option("", help="Run only this harness"),
    reps: int = typer.Option(0, help="Override the configured rep count"),
) -> None:
    """Execute trials and write evidence. Renders no report."""
    cfg = _load(config)
    rid = run_id or datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    _execute(cfg, out, rid, task, harness, reps or cfg.reps)


@app.command()
def report(run_dir: Path = typer.Argument(..., help="A run directory produced by `run`")) -> None:
    """Render report.md and report.json from an existing run. Runs no trials."""
    if not (run_dir / "manifest.json").is_file():
        console.print(f"[red]not a run directory[/red] {run_dir} (no manifest.json)")
        raise typer.Exit(2)
    _render(run_dir)


@app.command()
def evaluate(
    config: Path = typer.Argument(..., help="Path to eval.yaml"),
    out: Path = typer.Option(Path("runs"), help="Directory to write run artifacts into"),
    run_id: str = typer.Option("", help="Override the generated run id"),
) -> None:
    """Run trials, then render the report. Equivalent to `run` followed by `report`."""
    cfg = _load(config)
    rid = run_id or datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    run_dir = _execute(cfg, out, rid, "", "", cfg.reps)
    _render(run_dir)


if __name__ == "__main__":  # pragma: no cover
    app()

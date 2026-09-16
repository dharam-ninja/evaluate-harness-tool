"""Transitions, dimension rollups, flakiness, and the recommendation rule.

The tool's defensibility lives here. The rule is exported as data (`RULES`) so the report
prints the condition that actually fired, evaluated by the same objects the decision used.
A template restating the rule in prose could drift from the code; this cannot.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import (
    Confidence,
    CostSummary,
    DimensionSummary,
    EvaluationReport,
    Grader,
    GraderStatus,
    Outcome,
    Recommendation,
    TaskComparison,
    Transition,
    Trial,
    TrialStatus,
)

#: A candidate that is this much more expensive with nothing to show for it is negative.
COST_REGRESSION_PCT = 25.0


# --------------------------------------------------------------------------- outcomes


def trial_verdict(trial: Trial) -> bool | None:
    """True = passed, False = failed, None = cannot be trusted either way.

    None covers infrastructure errors and voided held-out overlays. Both are an absence
    of evidence, not evidence of a defect, and counting them as failures would attribute
    a network blip or a fouled overlay to the harness under test (NOTES.md T+2:40).
    """
    if not trial.measurable:
        return None
    return trial.critical_pass


def outcome_for(trials: list[Trial]) -> Outcome:
    """PASS iff every measured rep passed, FAIL iff every measured rep failed, else UNSTABLE.

    PLAN.md §4 words the FAIL arm as "all critical graders fail in all reps". Read
    literally that would make a rep where two of three critical graders passed neither a
    PASS nor a FAIL. The operative unit is the trial verdict -- did *every* critical
    grader pass -- so FAIL means every measured rep failed to clear that bar.
    """
    verdicts = [v for v in (trial_verdict(t) for t in trials) if v is not None]
    if not verdicts:
        return Outcome.UNMEASURED
    if all(verdicts):
        return Outcome.PASS
    if not any(verdicts):
        return Outcome.FAIL
    return Outcome.UNSTABLE


def transition_for(baseline: Outcome, candidate: Outcome) -> Transition:
    if Outcome.UNMEASURED in (baseline, candidate):
        return Transition.UNMEASURED
    if Outcome.UNSTABLE in (baseline, candidate):
        return Transition.UNSTABLE
    if baseline is Outcome.FAIL and candidate is Outcome.PASS:
        return Transition.IMPROVED
    if baseline is Outcome.PASS and candidate is Outcome.FAIL:
        return Transition.REGRESSED
    if baseline is Outcome.PASS:
        return Transition.UNCHANGED_PASS
    return Transition.UNCHANGED_FAIL


def dimension_outcome(trials: list[Trial], dimension: str) -> Outcome:
    """Roll one dimension up across the reps of a single harness.

    Applied to non-critical dimensions too. A dimension can disagree with itself between
    reps of the same harness -- ruff I001 appeared in one trial and vanished in an
    identical one (NOTES.md T+3:20) -- and a delta drawn from a self-inconsistent
    dimension is noise wearing a finding's clothes.
    """
    per_rep: list[bool] = []
    for t in trials:
        results = [g for g in t.graders if g.dimension == dimension]
        if not results or any(g.status is GraderStatus.VOID for g in results):
            continue
        per_rep.append(all(g.status is GraderStatus.PASS for g in results))
    if not per_rep:
        return Outcome.UNMEASURED
    if all(per_rep):
        return Outcome.PASS
    if not any(per_rep):
        return Outcome.FAIL
    return Outcome.UNSTABLE


def divergences_for(trials: list[Trial]) -> list[str]:
    """Flag trials whose visible tests passed while the held-out tests did not.

    The named failure mode from the assignment's evidence base: a patch that satisfies
    the suite and still implements the wrong thing.
    """
    out: list[str] = []
    for t in trials:
        acc = t.grader("acceptance")
        held = t.grader("heldout")
        if acc and held and acc.passed and held.status is GraderStatus.FAIL:
            out.append(
                f"{t.harness} rep {t.rep}: acceptance passed but held-out tests failed "
                f"-- the patch satisfies the visible suite and still misses the stated rule"
            )
    return out


# ------------------------------------------------------------------------------- cost


def _tokens(trial: Trial) -> float:
    """Every token the trial billed for, prompt cache included.

    Cache reads dominate the count and are the bulk of what is actually paid for, so
    excluding them would understate the real consumption the question asks about.
    """
    u = trial.usage
    return float(
        (u.input_tokens or 0)
        + (u.output_tokens or 0)
        + (u.cache_creation_input_tokens or 0)
        + (u.cache_read_input_tokens or 0)
    )


def cost_summary(comparisons: list[TaskComparison]) -> CostSummary:
    """Cost and wall-clock over successful trials, paired by task.

    Two exclusions, both load-bearing:
      - failed trials are dropped, because a candidate that gives up early is cheaper and
        worse, and averaging its failures in would reward that
      - tasks where only one arm succeeded are dropped entirely, because otherwise the
        two averages are taken over different task mixes and the delta measures which
        tasks each arm happened to solve rather than what either cost
    """
    b_cost: list[float] = []
    c_cost: list[float] = []
    b_wall: list[float] = []
    c_wall: list[float] = []
    b_tok: list[float] = []
    c_tok: list[float] = []
    counted = 0
    excluded = 0

    for comp in comparisons:
        arms = {}
        for name in ("baseline", "candidate"):
            ok = [
                t
                for t in comp.trials.get(name, [])
                if trial_verdict(t) is True
                and t.status is TrialStatus.COMPLETED
                and t.usage.total_cost_usd is not None
            ]
            arms[name] = ok
        if not arms["baseline"] or not arms["candidate"]:
            excluded += sum(len(v) for v in arms.values())
            continue
        counted += sum(len(v) for v in arms.values())
        b_cost += [t.usage.total_cost_usd or 0.0 for t in arms["baseline"]]
        c_cost += [t.usage.total_cost_usd or 0.0 for t in arms["candidate"]]
        b_wall += [t.wall_clock_s for t in arms["baseline"]]
        c_wall += [t.wall_clock_s for t in arms["candidate"]]
        b_tok += [_tokens(t) for t in arms["baseline"]]
        c_tok += [_tokens(t) for t in arms["candidate"]]

    def _mean(xs: list[float]) -> float | None:
        return round(statistics.fmean(xs), 4) if xs else None

    def _delta(a: float | None, b: float | None) -> float | None:
        if a is None or b is None or a == 0:
            return None
        return round((b - a) / a * 100.0, 1)

    summary = CostSummary(
        baseline_usd=_mean(b_cost),
        candidate_usd=_mean(c_cost),
        baseline_wall_s=_mean(b_wall),
        candidate_wall_s=_mean(c_wall),
        trials_counted=counted,
        trials_excluded=excluded,
    )
    summary.baseline_tokens = int(statistics.fmean(b_tok)) if b_tok else None
    summary.candidate_tokens = int(statistics.fmean(c_tok)) if c_tok else None
    summary.delta_pct = _delta(summary.baseline_usd, summary.candidate_usd)
    summary.wall_delta_pct = _delta(summary.baseline_wall_s, summary.candidate_wall_s)
    summary.token_delta_pct = _delta(
        summary.baseline_tokens, summary.candidate_tokens
    )

    summary.caveats = [
        (
            "Successful trials only. Failed and unmeasured trials are excluded, so a "
            "cheap failure cannot look like an efficiency gain."
        ),
        (
            "Paired by task: tasks where only one arm succeeded are dropped, so the two "
            "averages cover the same work."
        ),
        (
            "Cost is dominated by prompt-cache mechanics, and cache creation is priced "
            "far above cache read, so whichever arm runs first in a task pays more. "
            "Small deltas should not be read as harness effects."
        ),
    ]
    if excluded:
        summary.caveats.append(f"{excluded} successful trial(s) excluded by task pairing.")
    return summary


# ------------------------------------------------------------- the recommendation rule


@dataclass(frozen=True)
class RuleContext:
    """Everything the rule is allowed to look at. Keeps the predicates honest."""

    improvements: int
    regressions: int
    baseline_passes: int
    candidate_passes: int
    cost_delta_pct: float | None
    unstable: int
    unmeasured: int
    reps: int


@dataclass(frozen=True)
class Rule:
    name: str
    text: str
    recommendation: Recommendation
    predicate: Callable[[RuleContext], bool]


#: Evaluated top to bottom; the first match wins. This ordering IS the policy: a
#: regression outranks any amount of aggregate improvement.
RULES: list[Rule] = [
    Rule(
        name="regression_present",
        text="any task went PASS -> FAIL",
        recommendation=Recommendation.NEGATIVE,
        predicate=lambda c: c.regressions > 0,
    ),
    Rule(
        name="fewer_passes",
        text="the candidate passes fewer tasks than the baseline",
        recommendation=Recommendation.NEGATIVE,
        predicate=lambda c: c.candidate_passes < c.baseline_passes,
    ),
    Rule(
        name="costlier_for_nothing",
        text=f"no task improved and cost rose more than {COST_REGRESSION_PCT:.0f}%",
        recommendation=Recommendation.NEGATIVE,
        predicate=lambda c: c.improvements == 0
        and c.cost_delta_pct is not None
        and c.cost_delta_pct > COST_REGRESSION_PCT,
    ),
    Rule(
        name="improved_without_regressing",
        text="at least one task improved and none regressed",
        recommendation=Recommendation.POSITIVE,
        predicate=lambda c: c.improvements > 0 and c.regressions == 0,
    ),
    Rule(
        name="no_clear_signal",
        text="no task changed state either way",
        recommendation=Recommendation.INCONCLUSIVE,
        predicate=lambda c: True,
    ),
]


def apply_rules(ctx: RuleContext) -> tuple[Recommendation, Rule]:
    for rule in RULES:
        if rule.predicate(ctx):
            return rule.recommendation, rule
    raise AssertionError("the final rule must always match")  # pragma: no cover


def confidence_for(ctx: RuleContext) -> tuple[Confidence, list[str]]:
    """Never HIGH. A handful of tasks cannot support a strong claim either way."""
    reasons: list[str] = []
    if ctx.reps < 2:
        reasons.append("only one repetition per task, so non-determinism is unmeasured")
    if ctx.unstable:
        reasons.append(f"{ctx.unstable} task(s) gave different outcomes across reps")
    if ctx.unmeasured:
        reasons.append(f"{ctx.unmeasured} task(s) produced no trustworthy verdict")
    total = ctx.improvements + ctx.regressions
    if total == 0:
        reasons.append("no task changed state, so the comparison rests on unchanged results")
    return (Confidence.LOW if reasons else Confidence.MODERATE), reasons


# ---------------------------------------------------------------------------- assembly


def compare(trials: list[Trial], task_ids: list[str]) -> list[TaskComparison]:
    comparisons: list[TaskComparison] = []
    for task_id in task_ids:
        by_arm = {
            name: sorted(
                (t for t in trials if t.task_id == task_id and t.harness == name),
                key=lambda t: t.rep,
            )
            for name in ("baseline", "candidate")
        }
        outcomes = {name: outcome_for(ts) for name, ts in by_arm.items()}
        comparisons.append(
            TaskComparison(
                task_id=task_id,
                outcomes=outcomes,
                transition=transition_for(outcomes["baseline"], outcomes["candidate"]),
                trials=by_arm,
                divergences=divergences_for([t for ts in by_arm.values() for t in ts]),
            )
        )
    return comparisons


def summarise_dimensions(
    comparisons: list[TaskComparison], graders: list[Grader], dimensions: list[str]
) -> list[DimensionSummary]:
    out: list[DimensionSummary] = []
    for dim in dimensions:
        summary = DimensionSummary(
            dimension=dim, graders=[g.id for g in graders if g.dimension == dim]
        )
        for comp in comparisons:
            results = {
                arm: dimension_outcome(comp.trials.get(arm, []), dim)
                for arm in ("baseline", "candidate")
            }
            # Paired, like cost: a task counts only when BOTH arms produced a verdict for
            # this dimension. Counting a half-measured task would render as "candidate
            # 0/1" -- indistinguishable from the candidate failing, when in fact it was
            # never measured. Found by running build_report on a baseline-only run.
            if any(r is Outcome.UNMEASURED for r in results.values()):
                continue
            summary.total += 1
            for arm, result in results.items():
                if result is Outcome.PASS:
                    setattr(summary, f"{arm}_pass", getattr(summary, f"{arm}_pass") + 1)
                elif result is Outcome.UNSTABLE:
                    setattr(
                        summary, f"{arm}_unstable", getattr(summary, f"{arm}_unstable") + 1
                    )
        out.append(summary)
    return out


def _as_list(value: Any) -> list[str]:
    """Runs made before the model comparison landed stored a single string here.

    Reports must keep rendering from artifacts the current code did not write; a run is
    evidence, and evidence does not get re-run because a schema moved.
    """
    if value is None:
        return []
    return [value] if isinstance(value, str) else [str(v) for v in value]


def build_report(run_dir: Path) -> EvaluationReport:
    """Turn a run directory into the full EvaluationReport. Runs no trials."""
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    trials = [Trial(**t) for t in manifest["trials"]]
    graders = [Grader(**g) for g in manifest["graders"]]

    comparisons = compare(trials, manifest["tasks"])
    dimensions = summarise_dimensions(comparisons, graders, manifest.get("dimensions", []))
    cost = cost_summary(comparisons)

    counted = [c for c in comparisons if c.is_counted]
    ctx = RuleContext(
        improvements=sum(1 for c in counted if c.transition is Transition.IMPROVED),
        regressions=sum(1 for c in counted if c.transition is Transition.REGRESSED),
        baseline_passes=sum(1 for c in counted if c.outcomes["baseline"] is Outcome.PASS),
        candidate_passes=sum(1 for c in counted if c.outcomes["candidate"] is Outcome.PASS),
        cost_delta_pct=cost.delta_pct,
        unstable=sum(1 for c in comparisons if c.is_unstable),
        unmeasured=sum(1 for c in comparisons if c.transition is Transition.UNMEASURED),
        reps=manifest.get("reps", 0),
    )
    recommendation, rule = apply_rules(ctx)
    confidence, reasons = confidence_for(ctx)

    caveats = [f"Confidence is {confidence.value}: " + r for r in reasons]
    if manifest.get("jobs", 1) > 1:
        caveats.insert(
            0,
            f"jobs={manifest['jobs']}: trials ran concurrently, so wall-clock figures "
            f"for this run are not comparable.",
        )
    schedule = manifest.get("schedule")
    if schedule == "counterbalanced-task-rep":
        cost.caveats.append(
            "Arm order was counterbalanced across tasks and reps, so each arm took the "
            "cold-cache first slot equally often."
        )
    else:
        cost.caveats.append(
            "WARNING: this run predates arm-order counterbalancing. The baseline took the "
            "cold-cache first slot in every task, which measured at roughly -10% in the "
            "candidate's favour on an identical suite. Treat the cost delta as an upper "
            "bound on any real saving, not as a measurement."
        )

    # Permission denials are the evaluator's own footprint on the result. If one arm is
    # blocked more than the other it burns turns retrying, which inflates its cost and
    # its turn count for a reason that belongs to the harness config, not the harness.
    # Measured across full-01+full-02: add-cli-flag/candidate took 10 denials to
    # baseline's 2, because the candidate AGENTS.md tells the agent to run the checks
    # and more of its attempts hit a gap in the allowlist patterns.
    denials = {
        arm: sum(
            len(t.usage.permission_denials)
            for c in comparisons
            for t in c.trials.get(arm, [])
        )
        for arm in ("baseline", "candidate")
    }
    if sum(denials.values()):
        worse, better = sorted(denials, key=lambda a: -denials[a])
        if denials[worse] >= denials[better] * 2 + 2:
            cost.caveats.append(
                f"The evaluator blocked the {worse} arm {denials[worse]} time(s) against "
                f"{denials[better]} for {better}. Blocked attempts cost turns, so part of "
                f"this cost difference is the permission configuration, not the harness."
            )
        else:
            cost.caveats.append(
                f"Permission denials: {denials['baseline']} baseline, "
                f"{denials['candidate']} candidate."
            )

    # A dimension delta from a single run is unreplicated. full-01 reported conventions
    # 3/4 -> 0/4 with no within-run instability on the deciding task; full-02, identical
    # in every respect but trial order, reported 2/4 -> 3/4. The sign inverted.
    if ctx.reps <= 2 and any(d.delta for d in dimensions):
        caveats.append(
            "Dimension deltas below come from a single run at "
            f"{ctx.reps} rep(s) and are NOT replicated. On this suite a dimension delta "
            "has inverted between two runs that differed only in trial order. Treat any "
            "dimension row without a matching task transition as unconfirmed until a "
            "second run agrees with it."
        )

    errored = [t for t in trials if t.status is TrialStatus.ERROR]
    if errored:
        caveats.append(
            f"{len(errored)} trial(s) failed for infrastructure reasons and are excluded "
            f"from every outcome: "
            + ", ".join(f"{t.task_id}/{t.harness}/{t.rep}" for t in errored)
        )
    if any(c.divergences for c in comparisons):
        caveats.append(
            "At least one trial passed its visible tests and failed the held-out tests. "
            "A green suite did not mean correct behaviour here."
        )

    return EvaluationReport(
        run_id=manifest["run_id"],
        created_utc=manifest["created_utc"],
        change=manifest.get("change", ""),
        baseline_description=manifest.get("harnesses", {}).get("baseline", {}).get("description", ""),
        candidate_description=manifest.get("harnesses", {}).get("candidate", {}).get("description", ""),
        baseline_model=manifest.get("harnesses", {}).get("baseline", {}).get("model", ""),
        candidate_model=manifest.get("harnesses", {}).get("candidate", {}).get("model", ""),
        baseline_provider=(manifest.get("fairness", {}).get("models", {})
                           .get("baseline", {}).get("provider", "")),
        candidate_provider=(manifest.get("fairness", {}).get("models", {})
                            .get("candidate", {}).get("provider", "")),
        intended_difference=_as_list(manifest.get("fairness", {}).get("intended_difference")),
        controlled=bool(manifest.get("fairness", {}).get("controlled", False)),
        config=manifest.get("config"),
        reps=ctx.reps,
        jobs=manifest.get("jobs", 1),
        comparisons=comparisons,
        dimensions=dimensions,
        cost=cost,
        recommendation=recommendation,
        confidence=confidence,
        rule_fired=rule.name,
        rule_text=[f"{r.name}: {r.text} -> {r.recommendation.value}" for r in RULES],
        caveats=caveats,
    )

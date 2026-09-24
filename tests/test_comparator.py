"""Transitions, UNSTABLE handling, and the recommendation rule truth table.

Every branch of PLAN.md §4 gets a case, plus the two rules that are easiest to get subtly
wrong: UNSTABLE must never be rounded to PASS or FAIL, and cost must cover successful
trials only.
"""

from __future__ import annotations

import pytest

from harness_eval.comparator import (
    COST_REGRESSION_PCT,
    RULES,
    RuleContext,
    apply_rules,
    compare,
    confidence_for,
    cost_summary,
    dimension_outcome,
    outcome_for,
    transition_for,
)
from harness_eval.models import (
    Confidence,
    GraderResult,
    GraderStatus,
    Outcome,
    Recommendation,
    Transition,
    Trial,
    TrialStatus,
)


def _trial(
    *,
    task: str = "t1",
    harness: str = "baseline",
    rep: int = 0,
    critical_pass: bool = True,
    status: TrialStatus = TrialStatus.COMPLETED,
    cost: float | None = 1.0,
    wall: float = 10.0,
    void_critical: bool = False,
    lint_pass: bool | None = None,
) -> Trial:
    graders = [
        GraderResult(
            id="acceptance",
            dimension="correctness",
            critical=True,
            status=GraderStatus.VOID
            if void_critical
            else (GraderStatus.PASS if critical_pass else GraderStatus.FAIL),
        )
    ]
    if lint_pass is not None:
        graders.append(
            GraderResult(
                id="lint",
                dimension="conventions",
                critical=False,
                status=GraderStatus.PASS if lint_pass else GraderStatus.FAIL,
            )
        )
    t = Trial(task_id=task, harness=harness, rep=rep, status=status, graders=graders, wall_clock_s=wall)
    t.usage.total_cost_usd = cost
    return t


def _ctx(**kw: object) -> RuleContext:
    base = {
        "improvements": 0, "regressions": 0, "baseline_passes": 0, "candidate_passes": 0,
        "cost_delta_pct": None, "unstable": 0, "unmeasured": 0, "reps": 2,
    }
    return RuleContext(**{**base, **kw})  # type: ignore[arg-type]


# ------------------------------------------------------------------- outcome across reps


@pytest.mark.parametrize(
    ("verdicts", "expected"),
    [
        ([True, True], Outcome.PASS),
        ([False, False], Outcome.FAIL),
        ([True, False], Outcome.UNSTABLE),
        ([False, True], Outcome.UNSTABLE),
        ([True], Outcome.PASS),
        ([], Outcome.UNMEASURED),
    ],
)
def test_outcome_across_reps(verdicts: list[bool], expected: Outcome) -> None:
    trials = [_trial(rep=i, critical_pass=v) for i, v in enumerate(verdicts)]
    assert outcome_for(trials) is expected


def test_unmeasurable_reps_are_dropped_not_counted_as_failures() -> None:
    """An errored rep alongside a passing one must still read PASS, not UNSTABLE."""
    trials = [
        _trial(rep=0, critical_pass=True),
        _trial(rep=1, status=TrialStatus.ERROR, critical_pass=False),
    ]
    assert outcome_for(trials) is Outcome.PASS


def test_a_voided_heldout_overlay_makes_the_rep_unmeasurable() -> None:
    assert outcome_for([_trial(void_critical=True)]) is Outcome.UNMEASURED


# ----------------------------------------------------------------------------- transitions


@pytest.mark.parametrize(
    ("baseline", "candidate", "expected"),
    [
        (Outcome.FAIL, Outcome.PASS, Transition.IMPROVED),
        (Outcome.PASS, Outcome.FAIL, Transition.REGRESSED),
        (Outcome.PASS, Outcome.PASS, Transition.UNCHANGED_PASS),
        (Outcome.FAIL, Outcome.FAIL, Transition.UNCHANGED_FAIL),
        (Outcome.UNSTABLE, Outcome.PASS, Transition.UNSTABLE),
        (Outcome.PASS, Outcome.UNSTABLE, Transition.UNSTABLE),
        (Outcome.UNMEASURED, Outcome.PASS, Transition.UNMEASURED),
    ],
)
def test_transitions(baseline: Outcome, candidate: Outcome, expected: Transition) -> None:
    assert transition_for(baseline, candidate) is expected


def test_unstable_is_never_rounded_to_pass_or_fail() -> None:
    """Half this tool's credibility is in refusing to round. PLAN.md §4."""
    trials = [
        _trial(harness="baseline", rep=0, critical_pass=True),
        _trial(harness="baseline", rep=1, critical_pass=False),
        _trial(harness="candidate", rep=0, critical_pass=True),
        _trial(harness="candidate", rep=1, critical_pass=True),
    ]
    comp = compare(trials, ["t1"])[0]
    assert comp.baseline is Outcome.UNSTABLE
    assert comp.transition is Transition.UNSTABLE
    assert comp.is_counted is False  # excluded from improvement and regression counts


# ------------------------------------------------------------- recommendation truth table


def test_regression_outranks_any_amount_of_improvement() -> None:
    """The case the ordering exists for: 3 improvements and 1 regression is NEGATIVE."""
    rec, rule = apply_rules(_ctx(improvements=3, regressions=1, candidate_passes=5, baseline_passes=3))
    assert rec is Recommendation.NEGATIVE
    assert rule.name == "regression_present"


def test_fewer_passes_is_negative() -> None:
    rec, rule = apply_rules(_ctx(baseline_passes=4, candidate_passes=2))
    assert rec is Recommendation.NEGATIVE
    assert rule.name == "fewer_passes"


def test_costlier_for_nothing_is_negative() -> None:
    rec, rule = apply_rules(_ctx(improvements=0, cost_delta_pct=COST_REGRESSION_PCT + 1))
    assert rec is Recommendation.NEGATIVE
    assert rule.name == "costlier_for_nothing"


def test_cost_rise_just_under_the_threshold_is_not_negative() -> None:
    rec, _ = apply_rules(_ctx(improvements=0, cost_delta_pct=COST_REGRESSION_PCT - 0.1))
    assert rec is Recommendation.INCONCLUSIVE


def test_unknown_cost_does_not_trigger_the_cost_rule() -> None:
    """A missing cost must not be read as a cheap run (NOTES.md T+0:30)."""
    rec, _ = apply_rules(_ctx(improvements=0, cost_delta_pct=None))
    assert rec is Recommendation.INCONCLUSIVE


def test_improvement_without_regression_is_positive() -> None:
    rec, rule = apply_rules(_ctx(improvements=2, regressions=0, candidate_passes=2))
    assert rec is Recommendation.POSITIVE
    assert rule.name == "improved_without_regressing"


def test_no_change_at_all_is_inconclusive() -> None:
    rec, rule = apply_rules(_ctx(baseline_passes=3, candidate_passes=3))
    assert rec is Recommendation.INCONCLUSIVE
    assert rule.name == "no_clear_signal"


def test_every_rule_is_reachable_and_the_last_always_matches() -> None:
    assert {r.name for r in RULES} == {
        "regression_present", "fewer_passes", "costlier_for_nothing",
        "improved_without_regressing", "no_clear_signal",
    }
    assert RULES[-1].predicate(_ctx()) is True


# --------------------------------------------------------------------------- confidence


def test_confidence_is_never_high() -> None:
    conf, _ = confidence_for(_ctx(improvements=2, reps=2))
    assert conf is Confidence.MODERATE
    assert not hasattr(Confidence, "HIGH")


def test_single_rep_forces_low_confidence() -> None:
    conf, reasons = confidence_for(_ctx(improvements=1, reps=1))
    assert conf is Confidence.LOW
    assert any("one repetition" in r for r in reasons)


def test_any_unstable_task_forces_low_confidence() -> None:
    conf, reasons = confidence_for(_ctx(improvements=1, reps=2, unstable=1))
    assert conf is Confidence.LOW
    assert any("different outcomes across reps" in r for r in reasons)


def test_an_all_unstable_suite_is_inconclusive_and_low() -> None:
    ctx = _ctx(reps=2, unstable=4)
    rec, rule = apply_rules(ctx)
    conf, _ = confidence_for(ctx)
    assert rec is Recommendation.INCONCLUSIVE
    assert rule.name == "no_clear_signal"
    assert conf is Confidence.LOW


# --------------------------------------------------------------------------------- cost


def test_cost_covers_successful_trials_only() -> None:
    """A candidate that fails fast is cheaper and worse. It must not read as efficient."""
    trials = [
        _trial(harness="baseline", rep=0, critical_pass=True, cost=1.00),
        _trial(harness="candidate", rep=0, critical_pass=True, cost=0.90),
        _trial(harness="candidate", rep=1, critical_pass=False, cost=0.01),
    ]
    comp = compare(trials, ["t1"])
    summary = cost_summary(comp)
    assert summary.candidate_usd == 0.90  # the $0.01 failure is not averaged in
    assert summary.delta_pct == -10.0


def test_cost_is_paired_by_task() -> None:
    """Tasks only one arm solved are dropped, or the averages cover different work."""
    trials = [
        _trial(task="t1", harness="baseline", critical_pass=True, cost=1.0),
        _trial(task="t1", harness="candidate", critical_pass=True, cost=1.0),
        _trial(task="t2", harness="baseline", critical_pass=True, cost=9.0),
        _trial(task="t2", harness="candidate", critical_pass=False, cost=9.0),
    ]
    summary = cost_summary(compare(trials, ["t1", "t2"]))
    assert summary.baseline_usd == 1.0  # t2's expensive baseline success is excluded
    assert summary.trials_excluded == 1
    assert any("Paired by task" in c for c in summary.caveats)


def test_raw_spend_is_reported_even_when_nothing_is_comparable() -> None:
    """mixed-01's shape: one arm passes nothing, so the paired comparison is withheld.

    Every compared figure correctly reads n/a, which on its own is indistinguishable from
    "the tool failed to capture cost". The raw totals say what the run actually cost.
    """
    trials = [
        _trial(harness="baseline", rep=0, critical_pass=False, cost=0.0),
        _trial(harness="baseline", rep=1, critical_pass=False, cost=0.0),
        _trial(harness="candidate", rep=0, critical_pass=True, cost=0.30),
        _trial(harness="candidate", rep=1, critical_pass=True, cost=0.20),
    ]
    summary = cost_summary(compare(trials, ["t1"]))

    assert summary.baseline_usd is None and summary.candidate_usd is None
    assert summary.trials_counted == 0
    assert summary.baseline_total_usd == 0.0
    assert summary.candidate_total_usd == 0.50
    assert summary.baseline_trial_count == 2
    assert summary.candidate_trial_count == 2
    assert "baseline passed 0 of 2" in summary.not_comparable_reason


def test_raw_spend_counts_failed_trials_that_the_comparison_drops() -> None:
    """The two numbers answer different questions and must not agree by accident."""
    trials = [
        _trial(harness="baseline", rep=0, critical_pass=True, cost=1.00),
        _trial(harness="candidate", rep=0, critical_pass=True, cost=0.90),
        _trial(harness="candidate", rep=1, critical_pass=False, cost=0.01),
    ]
    summary = cost_summary(compare(trials, ["t1"]))
    assert summary.candidate_usd == 0.90            # mean over successes only
    assert summary.candidate_total_usd == 0.91      # every trial, failure included
    assert not summary.not_comparable_reason        # the comparison still stands


def test_no_reason_is_given_when_the_comparison_succeeded() -> None:
    """The explanation appears only where it explains something."""
    trials = [
        _trial(harness="baseline", cost=1.0),
        _trial(harness="candidate", cost=2.0),
    ]
    summary = cost_summary(compare(trials, ["t1"]))
    assert summary.not_comparable_reason == ""
    assert summary.baseline_total_usd == 1.0


def test_cost_caveats_always_mention_the_cache_mechanism() -> None:
    summary = cost_summary([])
    assert any("prompt-cache" in c for c in summary.caveats)


# ---------------------------------------------------------------------------- dimensions


def test_a_dimension_that_disagrees_with_itself_across_reps_is_unstable() -> None:
    """ruff I001 appeared then vanished on identical work -- NOTES.md T+3:20."""
    trials = [
        _trial(rep=0, lint_pass=True),
        _trial(rep=1, lint_pass=False),
    ]
    assert dimension_outcome(trials, "conventions") is Outcome.UNSTABLE


def test_a_stable_dimension_rolls_up_cleanly() -> None:
    trials = [_trial(rep=0, lint_pass=True), _trial(rep=1, lint_pass=True)]
    assert dimension_outcome(trials, "conventions") is Outcome.PASS


def test_a_dimension_with_no_graders_is_unmeasured_not_passing() -> None:
    assert dimension_outcome([_trial()], "efficiency") is Outcome.UNMEASURED


# -------------------------------------------------------------------------- divergences


def test_acceptance_passing_while_heldout_fails_is_surfaced() -> None:
    """The failure mode the whole fidelity dimension exists to catch."""
    trial = _trial()
    trial.graders = [
        GraderResult(id="acceptance", dimension="correctness", critical=True, status=GraderStatus.PASS),
        GraderResult(id="heldout", dimension="fidelity", critical=True, status=GraderStatus.FAIL),
    ]
    comp = compare([trial], ["t1"])[0]
    assert len(comp.divergences) == 1
    assert "acceptance passed but held-out tests failed" in comp.divergences[0]


# ------------------------------------------------------------------------- assembly


def _manifest(trials: list[Trial], **kw: object) -> dict:
    base = {
        "run_id": "test-run",
        "created_utc": "2026-09-15T00:00:00+00:00",
        "config": "examples/eval.yaml",
        "reps": 2,
        "jobs": 1,
        "dimensions": ["correctness", "conventions"],
        "tasks": sorted({t.task_id for t in trials}),
        "graders": [
            {"id": "acceptance", "command": "x", "dimension": "correctness", "critical": True},
            {"id": "lint", "command": "y", "dimension": "conventions", "critical": False},
        ],
        "trials": [t.model_dump(mode="json") for t in trials],
    }
    return {**base, **kw}


def _write_run(tmp_path, trials: list[Trial], **kw: object):
    import json
    (tmp_path / "manifest.json").write_text(json.dumps(_manifest(trials, **kw)), encoding="utf-8")
    return tmp_path


def test_build_report_end_to_end_on_an_improvement(tmp_path) -> None:
    from harness_eval.comparator import build_report

    trials = [
        _trial(harness="baseline", rep=r, critical_pass=False, cost=1.0, lint_pass=True)
        for r in (0, 1)
    ] + [
        _trial(harness="candidate", rep=r, critical_pass=True, cost=1.1, lint_pass=True)
        for r in (0, 1)
    ]
    rep = build_report(_write_run(tmp_path, trials))

    assert rep.recommendation is Recommendation.POSITIVE
    assert rep.rule_fired == "improved_without_regressing"
    assert rep.confidence is Confidence.MODERATE
    assert len(rep.improvements) == 1 and not rep.regressions
    # the printed rule is generated from RULES, so it cannot drift from the code
    assert len(rep.rule_text) == len(RULES)
    assert any("improved_without_regressing" in line for line in rep.rule_text)


def test_build_report_excludes_errored_trials_and_says_so(tmp_path) -> None:
    from harness_eval.comparator import build_report

    trials = [
        _trial(harness="baseline", rep=0, critical_pass=True),
        _trial(harness="baseline", rep=1, status=TrialStatus.ERROR, critical_pass=False),
        _trial(harness="candidate", rep=0, critical_pass=True),
        _trial(harness="candidate", rep=1, critical_pass=True),
    ]
    rep = build_report(_write_run(tmp_path, trials))
    assert rep.comparisons[0].baseline is Outcome.PASS  # the errored rep did not drag it down
    assert any("infrastructure reasons" in c for c in rep.caveats)
    assert any("t1/baseline/1" in c for c in rep.caveats)


def test_build_report_warns_when_trials_ran_concurrently(tmp_path) -> None:
    from harness_eval.comparator import build_report

    rep = build_report(_write_run(tmp_path, [_trial()], jobs=4))
    assert any("wall-clock" in c and "jobs=4" in c for c in rep.caveats)


def test_dimension_summary_counts_noise_separately_from_passes(tmp_path) -> None:
    from harness_eval.comparator import build_report

    trials = [
        _trial(harness="baseline", rep=0, lint_pass=True),
        _trial(harness="baseline", rep=1, lint_pass=False),   # flaps
        _trial(harness="candidate", rep=0, lint_pass=True),
        _trial(harness="candidate", rep=1, lint_pass=True),
    ]
    rep = build_report(_write_run(tmp_path, trials))
    conventions = next(d for d in rep.dimensions if d.dimension == "conventions")
    assert conventions.baseline_pass == 0
    assert conventions.baseline_unstable == 1
    assert conventions.candidate_pass == 1
    assert conventions.noisy is True  # a delta here would be noise, and the report must say so


def test_build_report_headlines_a_heldout_divergence(tmp_path) -> None:
    """The report must say plainly when a green suite did not mean correct behaviour."""
    from harness_eval.comparator import build_report

    trial = _trial(harness="candidate", rep=0)
    trial.graders = [
        GraderResult(id="acceptance", dimension="correctness", critical=True, status=GraderStatus.PASS),
        GraderResult(id="heldout", dimension="fidelity", critical=True, status=GraderStatus.FAIL),
    ]
    rep = build_report(_write_run(tmp_path, [trial], reps=1))
    assert any("A green suite did not mean correct behaviour" in c for c in rep.caveats)


def test_a_dimension_is_not_counted_when_one_arm_was_never_measured(tmp_path) -> None:
    """Half-measured must not render as "candidate 0/1", which reads as a failure."""
    from harness_eval.comparator import build_report

    rep = build_report(_write_run(tmp_path, [_trial(harness="baseline", lint_pass=True)], reps=1))
    conventions = next(d for d in rep.dimensions if d.dimension == "conventions")
    assert conventions.total == 0
    assert conventions.baseline_pass == 0
    assert conventions.candidate_pass == 0

"""Domain model: Task, AgentHarness, Trial, Grader, TaskComparison, EvaluationReport.

The vocabulary follows Anthropic's "Demystifying evals for AI agents" (Jan 2026) where it
overlaps, and PLAN.md §2 exactly. `AgentHarness` is the evaluand; this package is the
evaluation harness. These names appear verbatim in DESIGN.md §1, so they are the tool's
vocabulary and not an implementation detail.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TrialStatus(str, Enum):
    """What happened to the agent run itself, independent of grading."""

    COMPLETED = "completed"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    ERROR = "error"


class GraderStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    TIMEOUT = "timeout"
    VOID = "void"
    """Could not be measured. Must not be read as either a pass or a fail.

    A held-out overlay whose destination already existed is the case this exists for:
    the agent may have seen the tests, so the number is untrustworthy in both
    directions. Forcing it to FAIL would report a defect nobody demonstrated.
    """


class Outcome(str, Enum):
    """A task's verdict for one harness, aggregated across reps."""

    PASS = "pass"
    FAIL = "fail"
    UNSTABLE = "unstable"
    UNMEASURED = "unmeasured"
    """No rep produced a trustworthy verdict. Not a failure -- an absence of evidence."""


class Transition(str, Enum):
    IMPROVED = "FAIL->PASS"
    REGRESSED = "PASS->FAIL"
    UNCHANGED_PASS = "PASS->PASS"
    UNCHANGED_FAIL = "FAIL->FAIL"
    UNSTABLE = "UNSTABLE"
    UNMEASURED = "UNMEASURED"


class Recommendation(str, Enum):
    POSITIVE = "POSITIVE SIGNAL"
    NEGATIVE = "NEGATIVE"
    INCONCLUSIVE = "INCONCLUSIVE"


class Confidence(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"


# --------------------------------------------------------------------------- the plan


class Grader(BaseModel):
    """Logic that scores one dimension of a trial. One generic shape, config-declared."""

    id: str
    command: str
    dimension: str
    critical: bool = False
    overlay: str | None = None
    timeout_s: int = 300


class AgentHarness(BaseModel):
    """The evaluand. Everything here can differ between the two arms."""

    name: str = ""
    description: str = ""
    command: str
    model: str
    endpoint: str | None = None
    """Base URL of the model provider, when it is not the CLI's default.

    Exported to the trial as ANTHROPIC_BASE_URL, which is how Claude Code is pointed at
    an alternative (OpenAI-compatible or Anthropic-compatible) endpoint. A harness that
    shells out to a different CLI entirely can set whatever it needs via `env` instead.
    """

    budget: float | None = None
    instructions: Path | None = None
    config_dir: Path | None = None
    """A directory copied into the workspace root before the initial commit.

    Carries agent configuration that is not a single prose file -- a `.claude/` with
    hooks, for instance. Applied exactly like `instructions`: part of the environment
    under test, committed as the baseline so it never shows up in the agent's patch.
    """

    env: dict[str, str] = Field(default_factory=dict)

    @property
    def provider(self) -> str:
        """Human-readable provider, for the manifest and the report header."""
        return self.endpoint or "default (CLI-configured)"


class Task(BaseModel):
    """A single scenario: repo state, prompt, visible tests, held-out tests."""

    id: str
    prompt: str
    acceptance_tests: Path
    heldout_tests: Path
    notes: str = ""


class EvalConfig(BaseModel):
    """One experiment: which harnesses, on which tasks, graded how, how many times."""

    repo: Path
    change: str = ""
    harnesses: dict[str, AgentHarness]
    tasks: list[Task]
    graders: list[Grader]
    dimensions: list[str]
    intended_difference: list[str] = Field(default_factory=lambda: ["instructions"])
    """Which harness fields are deliberately allowed to differ between the arms.

    Everything NOT listed here must be identical, and the run manifest records whether
    that held. Declaring the difference makes an intentional model comparison auditable
    instead of indistinguishable from an accidental one.
    """

    reps: int = 2
    timeout_s: int = 600
    jobs: int = 1
    source: Path | None = None

    @property
    def baseline(self) -> AgentHarness:
        return self.harnesses["baseline"]

    @property
    def candidate(self) -> AgentHarness:
        return self.harnesses["candidate"]


# --------------------------------------------------------------------------- evidence


class Usage(BaseModel):
    """Parsed from the agent's JSON envelope. Every field is optional on purpose:
    an absent field is null, never 0. A zero cost is indistinguishable from a free
    run and would corrupt the cost dimension (NOTES.md T+0:30).
    """

    total_cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    num_turns: int | None = None
    duration_ms: int | None = None
    duration_api_ms: int | None = None
    model_usage: dict[str, Any] = Field(default_factory=dict)
    permission_denials: list[Any] = Field(default_factory=list)
    is_error: bool | None = None
    subtype: str | None = None
    session_id: str | None = None


class GraderResult(BaseModel):
    """One grader's verdict on one trial, with a pointer to its log."""

    id: str
    dimension: str
    critical: bool
    status: GraderStatus
    exit_code: int | None = None
    duration_s: float = 0.0
    log_path: str | None = None
    reason: str | None = None

    @property
    def passed(self) -> bool:
        return self.status is GraderStatus.PASS


class Trial(BaseModel):
    """One run of one AgentHarness on one Task, from a clean workspace."""

    task_id: str
    harness: str
    rep: int
    status: TrialStatus
    exit_code: int | None = None
    wall_clock_s: float = 0.0
    usage: Usage = Field(default_factory=Usage)
    files_changed: list[str] = Field(default_factory=list)
    patch_bytes: int = 0
    tools_run: list[str] = Field(default_factory=list)
    tool_calls: dict[str, int] = Field(default_factory=dict)
    """Which agent tools were invoked, and how often. From a stream-json transcript."""

    files_inspected: list[str] = Field(default_factory=list)
    """Files the agent read, grepped or globbed. Evidence that it looked before writing."""

    hook_events: int = 0
    """Hook lifecycle events seen in the transcript.

    A hook that silently does not fire would make a comparison look like a null result
    for the wrong reason, so whether it ran is recorded rather than assumed.
    """

    tests_modified: list[str] = Field(default_factory=list)
    """Any test file the agent changed -- the cheapest way to fake a passing grader."""

    """Which verification tools the AGENT ran, captured before any grader runs.

    A harness can only be credited with changing behaviour if the behaviour changed.
    Detected from the cache directories each tool leaves in the workspace, snapshotted
    at patch-capture time -- afterwards the graders run the same tools and the evidence
    would be destroyed.
    """
    graders: list[GraderResult] = Field(default_factory=list)
    error: str | None = None
    workspace: str | None = None
    trial_dir: str | None = None

    @property
    def critical_pass(self) -> bool:
        """True only if every critical grader passed. No criticals means no verdict."""
        criticals = [g for g in self.graders if g.critical]
        return bool(criticals) and all(g.passed for g in criticals)

    @property
    def measurable(self) -> bool:
        """False when this trial cannot yield an honest verdict.

        Excluded from outcome computation rather than counted as a failure, for the
        same reason infrastructure errors are (NOTES.md T+2:40): a number we could not
        measure is not evidence of a defect.
        """
        if self.status is TrialStatus.ERROR:
            return False
        return not any(
            g.critical and g.status is GraderStatus.VOID for g in self.graders
        )

    def grader(self, grader_id: str) -> GraderResult | None:
        return next((g for g in self.graders if g.id == grader_id), None)


# --------------------------------------------------------------------------- comparison


class TaskComparison(BaseModel):
    """Paired baseline-vs-candidate result for one task, with the transition."""

    task_id: str
    outcomes: dict[str, Outcome]
    transition: Transition
    trials: dict[str, list[Trial]] = Field(default_factory=dict)
    divergences: list[str] = Field(default_factory=list)

    @property
    def baseline(self) -> Outcome:
        return self.outcomes["baseline"]

    @property
    def candidate(self) -> Outcome:
        return self.outcomes["candidate"]

    @property
    def is_counted(self) -> bool:
        """Only stable, measured tasks feed the improvement and regression counts."""
        return self.transition not in (Transition.UNSTABLE, Transition.UNMEASURED)

    @property
    def is_unstable(self) -> bool:
        """Unstable tasks are excluded from improvement and regression counts.

        Rounding UNSTABLE to PASS or FAIL would manufacture a signal the reps did not
        support -- see PLAN.md §4.
        """
        return self.transition is Transition.UNSTABLE


class DimensionSummary(BaseModel):
    """One dimension rolled up across tasks, per harness."""

    dimension: str
    baseline_pass: int = 0
    candidate_pass: int = 0
    baseline_unstable: int = 0
    candidate_unstable: int = 0
    total: int = 0
    graders: list[str] = Field(default_factory=list)

    @property
    def delta(self) -> int:
        return self.candidate_pass - self.baseline_pass

    @property
    def noisy(self) -> bool:
        """True when either arm disagreed with itself across reps on this dimension.

        A dimension can flip between reps of the SAME harness (NOTES.md T+3:20 saw ruff
        I001 appear and vanish on identical work). Reporting a delta from a dimension
        that is not self-consistent would dress up noise as a finding.
        """
        return bool(self.baseline_unstable or self.candidate_unstable)


class CostSummary(BaseModel):
    """Cost and wall-clock, over successful trials only.

    Caveats are carried in the model rather than written into a template, so the number
    and the reason it needs qualifying cannot drift apart (NOTES.md T+0:30).
    """

    baseline_usd: float | None = None
    candidate_usd: float | None = None
    delta_pct: float | None = None
    baseline_wall_s: float | None = None
    candidate_wall_s: float | None = None
    wall_delta_pct: float | None = None
    baseline_tokens: int | None = None
    candidate_tokens: int | None = None
    token_delta_pct: float | None = None
    trials_counted: int = 0
    trials_excluded: int = 0
    caveats: list[str] = Field(default_factory=list)
    impact_threshold_pct: float = 25.0

    @property
    def impact(self) -> str:
        """Plain-language verdict on the cost dimension alone."""
        if self.delta_pct is None:
            return "Not measured"
        if self.delta_pct > self.impact_threshold_pct:
            return "Negative impact"
        if self.delta_pct < -self.impact_threshold_pct:
            return "Positive impact"
        return "No material impact"


class EvaluationReport(BaseModel):
    """The full comparison across all tasks, trials and graders, with evidence links."""

    run_id: str
    created_utc: str
    config: str | None = None
    baseline_name: str = "baseline"
    candidate_name: str = "candidate"
    change: str = ""
    baseline_description: str = ""
    candidate_description: str = ""
    baseline_model: str = ""
    candidate_model: str = ""
    baseline_provider: str = ""
    candidate_provider: str = ""
    intended_difference: list[str] = Field(default_factory=list)
    controlled: bool = False
    reps: int = 0
    jobs: int = 1
    comparisons: list[TaskComparison] = Field(default_factory=list)
    dimensions: list[DimensionSummary] = Field(default_factory=list)
    cost: CostSummary = Field(default_factory=CostSummary)
    recommendation: Recommendation = Recommendation.INCONCLUSIVE
    confidence: Confidence = Confidence.LOW
    rule_fired: str = ""
    rule_text: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)

    @property
    def improvements(self) -> list[TaskComparison]:
        return [c for c in self.comparisons if c.transition is Transition.IMPROVED]

    @property
    def regressions(self) -> list[TaskComparison]:
        return [c for c in self.comparisons if c.transition is Transition.REGRESSED]

    @property
    def unstable(self) -> list[TaskComparison]:
        return [c for c in self.comparisons if c.is_unstable]

    @property
    def unmeasured(self) -> list[TaskComparison]:
        return [c for c in self.comparisons if c.transition is Transition.UNMEASURED]

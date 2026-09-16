# Design note: harness-eval

## 1. Concepts, and why

The vocabulary is adopted from Anthropic's [*Demystifying evals for AI
agents*](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (Jan 2026)
rather than reinvented. Given how closely this problem tracks that post, inventing parallel
terms would have made the work harder to compare against, not easier.

| Concept | What it is |
|---|---|
| `Task` | repo state + prompt + visible tests + held-out tests |
| `AgentHarness` | the evaluand: command, model, endpoint, instructions, env, budget |
| `Trial` | one run of one harness on one task, from a clean workspace |
| `Grader` | a command producing pass/fail + a log for one dimension |
| `TaskComparison` | paired baseline-vs-candidate for one task, with the transition |
| `EvaluationReport` | all comparisons, dimensions, the verdict, and links to the evidence |

One distinction the post warns about and I kept: their **agent harness** is the thing under
test; their **evaluation harness** is this tool. Naming them apart avoids a self-referential
mess.

## 2. The five hardest decisions

1. **Paired Δ, never a composite score.** One number would hide "correct but slower" and
   "cheaper but wrong", the exact trade-offs the tool exists to surface. Cost: no headline
   figure to put in a slide.
2. **Held-out tests as a first-class grader.** Each task ships visible tests the agent may
   run and hidden tests overlaid only *after* the patch is taken. Cost: every task takes
   twice as long to author. Benefit: `add-cli-flag` passed its visible suite in 8/8 trials
   and failed held-out in 8/8: a green suite that meant nothing.
3. **Fresh copy, not `git worktree`.** Worktrees share an object store, so trial N could read
   trial N-1's history, and Claude Code hooks are documented as not firing reliably inside
   one. Cost: slower setup per trial. Benefit: no cross-trial leakage, and Windows-safe.
4. **`run` and `report` are separate commands.** Trials cost money and are non-deterministic;
   rendering is neither. Every report fix re-renders from `runs/` in seconds. This paid for
   itself when a session died mid-run: the expensive half was lost, the cheap half was never
   at risk.
5. **UNSTABLE is an outcome, not a rounding problem.** When reps of the *same* harness
   disagree, the task is excluded from the improvement and regression counts rather than
   rounded to PASS or FAIL. Cost: fewer countable results. Benefit: see §4.

Runner-up, and the one I would promote on reflection: **instrumenting `tools_run`** by
detecting `.pytest_cache/`, `.ruff_cache/` and `.mypy_cache/` *before* the graders execute.
It turned "the candidate made no difference" into "the candidate ran ruff and mypy 4/4 times
where the baseline ran them 0/4, and it changed no outcome", which is a different and more useful
finding.

## 3. What I cut, and why

I chose not to spend the budget on: a **web dashboard** (Markdown + JSON is the same decision
surface at a fraction of the build risk); **parallel execution by default** (it makes
wall-clock incomparable, and `--jobs` exists with a warning banner for when time matters more
than that number); **native SDK integrations** (one shell adapter demonstrates the abstraction;
swapping Claude Code for a local model was a config change plus a runner script, no
evaluator change); **an LLM-as-judge grader** (hard to calibrate defensibly, and every
question I cared about turned out to be expressible as a deterministic check); **a single
composite score** (§2.1); and **significance testing** (a four-task suite cannot support
inferential claims, and pretending otherwise is worse than reporting paired outcomes).

## 4. One result I did not trust

`full-01` reported the conventions dimension at **3/4 -> 0/4**. The driver was
`refactor-config`: the candidate failed `mypy --strict` in **both** reps, the baseline passed
in **both**. Perfectly self-consistent inside the run, so the UNSTABLE flag never fired on
that task. I wrote it up as *"the one consistent effect"*.

Then I ran the identical suite a second time, changing only trial order. `full-02` reported
**2/4 -> 3/4**. The sign inverted.

Hand inspection found the cause. Both failing trials had written the same thing:

```python
coerce = _COERCERS.get(key, lambda v: v)   # unannotated lambda; mypy strict rejects it
```

Correlation across all eight `refactor-config` trials was perfect: lambda present -> FAIL,
absent -> PASS, 8/8. **The tool was right about every individual trial. My reading of them was
wrong**. A 2-of-2 versus 0-of-2 split is what a coin flip looks like at n=2, and which arm
drew it was chance.

Three things changed as a result. Dimension deltas at <=2 reps now render with an explicit
"NOT REPLICATED" caveat naming this inversion. `DimensionSummary.noisy` surfaces when either
arm disagreed with itself. And I stopped treating within-run consistency as evidence: the
tool detects instability *inside* a run and cannot see it *between* runs, which is a stated
limit of the design rather than a bug.

The general lesson, which cost me three separate bugs to learn: **a green unit suite protects
the logic, but only running the thing on real artifacts catches the cases where the logic is
right and the presentation lies.**

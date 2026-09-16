# harness-eval: Implementation Plan

End-to-end plan for the take-home. Supersedes the brief (`harness-eval-problem-statement.md`) where they disagree; every deviation is marked **[gap]** with the reason.

---

## 0. Resolved assumptions

The brief leaves these "open"; there is nobody to ask, so they are decided here and will be restated in `DESIGN.md` as explicit assumptions.

| Question | Decision | Why |
|---|---|---|
| Time budget | 8h cap, 7h target | Requirement says "six to eight hours" |
| Scale | 4 tasks x 2 harnesses x 2 reps = 16 trials | Wall-clock arithmetic, see §5 |
| Statistical rigor | Raw paired outcomes only. No CIs, no bootstrap | n=4 cannot support inference; saying so is the stronger claim |
| Agent products | One adapter (Claude Code). `AgentAdapter` protocol so a 2nd is config-only | Brief §11 cut; cross-product cost is not apples-to-apples anyway |
| Demo repo | Purpose-built small Python repo, committed to this repo | Need control over which tasks are weakly tested |
| Change under test | `AGENTS.md` present (candidate) vs absent (baseline) | Cheapest to run, visible effect, avoids the `--bare` trap (brief §6.2) |
| Business fidelity | Held-out tests (deterministic) + manual checklist section. No LLM judge | **[gap]** brief deferred this; see §2 |
| Cite Anthropic evals post | Yes, in `DESIGN.md` | Vocabulary overlap is obvious; silent reinvention reads worse |
| Platform | Windows-native, no WSL | **[gap]** brief assumes POSIX; see §3 |

---

## 1. Gaps being closed vs. the brief

1. **Process artifacts are a deliverable**, the brief's definition-of-done omits them entirely. Captured from minute zero, not retrofitted. §7.
2. **Business fidelity via held-out tests**, the brief deferred the one quality dimension the requirement names explicitly. §2.
3. **`run` / `report` split**, the brief implies a single `evaluate`. Re-rendering must not cost a re-run. §4.
4. **Wall-clock and spend budgeted**, the brief flags task count as open, never costs it. §5.
5. **Windows-native execution**, the brief assumes POSIX shell, worktrees, `timeout`. §3.
6. **Flakiness is first-class**, unstable tasks excluded from improvement/regression counts and shown prominently. The brief mentions reps but not what to do when reps disagree. §4.
7. **Deterministic, printed recommendation rule**, the brief shows a verdict line but no rule. §4.
8. **Committed sample run**, reviewer renders the report offline, no CLI, no spend. §6.
9. **CLI flags verified before design**, the brief's flag table is asserted, not checked. §3.
10. **`DESIGN.md` includes "concepts and why"**, the brief's DoD dropped it from the one-pager. §8.

---

## 2. Domain model

Adopting Anthropic's published vocabulary (brief §6.1), cited rather than reinvented.

| Concept | Definition |
|---|---|
| `Task` | repo state + prompt + graders + held-out tests |
| `AgentHarness` | the evaluand: command template, model, instructions, env, config overlay |
| `Trial` | one run of one harness on one task, from a fresh workspace |
| `Grader` | a command producing pass/fail + log for one dimension |
| `TaskComparison` | paired baseline vs candidate for one task, with the transition |
| `EvaluationReport` | all comparisons + dimensions + recommendation + evidence links |

**Dimensions**, mapped 1:1 to the requirement's four quality claims:

| Requirement phrase | Dimension | Graders |
|---|---|---|
| "the code works" | Correctness | `acceptance` (visible) |
| "does what the business asked" | Fidelity | `heldout` (hidden) + manual checklist |
|, | Regression safety | `regressions` (full suite) |
| "follows the team's conventions" | Conventions | `lint`, `types` |
| "did not cost a fortune in tokens" | Cost | usd, tokens, wall-clock (successful trials only) |
|, | Reliability | agreement across reps |

**Held-out tests, the key addition.** Each task ships two test sets:

- `tests/`: copied into the workspace, the agent sees them, the `acceptance` grader runs them.
- `heldout/<task>/`: **never copied into the workspace.** Overlaid onto the finished workspace after the agent exits, then run as the `heldout` grader.

A patch that passes `acceptance` and fails `heldout` is "passed the tests, did the wrong thing", the exact failure mode in Wang et al. (brief §4). It is deterministic, free, and is the most likely source of the §8 distrust case.

---

## 3. Platform decisions (Windows)

- **Python 3.10.4 is sufficient** (PEP 604 unions land in 3.10). No upgrade. venv + pip; skip `uv`: not worth the install time. Note the choice in `DESIGN.md`.
- **No worktrees, no symlinks.** Isolation = copy the working tree *excluding* `.git`, then `git init && git add -A && git commit`. Fresh single-commit history per trial. This sidesteps both brief §6.2 gotchas (worktree hooks not firing, cross-trial history leakage) and is Windows-safe.
- **No shell `timeout`.** Use `subprocess.run(..., timeout=N)` and kill the process tree.
- **All commands are config strings**, run with `shell=True` so `pytest -q` etc. resolve via the workspace venv. Document that graders inherit that venv.
- **Step 0 gate:** run `claude --help` and record what actually exists in `NOTES.md`. The brief asserts `--bare`, `--no-session-persistence`, `--max-budget-usd`, `--fallback-model`, `--ephemeral`. Design only around flags confirmed present.

---

## 4. Architecture

```
eval.yaml
   |
   v
[config]  pydantic models, `validate` command
   |
   v
[run] --------------------------------------------- per trial:
   |   workspace.py   fresh copy, git init
   |   adapters.py    ShellAgentAdapter -> claude -p ... --output-format json
   |   evidence.py    patch.diff, cost/tokens/turns, duration, exit code
   |   graders.py     CommandGrader xN (+ heldout overlay)
   v
runs/<run-id>/
   manifest.json
   trials/<task>/<harness>/<rep>/
       patch.diff  transcript.json  result.json  graders/<id>.log
   |
   v
[report]
   comparator.py  transitions, dimensions, flakiness, recommendation rule
   report.py      jinja2 -> report.md + report.json + tasks/<task>.md
```

`evaluate` = `run` then `report`. **The split is the point:** every report fix in the last two hours re-renders from `runs/` in seconds instead of re-spending an hour and real money.

**Repo layout**

```
harness-eval/
  pyproject.toml  README.md  DESIGN.md  PROCESS.md  NOTES.md  AGENTS.md
  prompts/                    # verbatim prompts used to build the tool
  transcripts/                # >=1 complete agent session
  src/harness_eval/
    cli.py config.py models.py workspace.py adapters.py
    graders.py evidence.py comparator.py report.py templates/
  examples/
    demo-repo/                # the system under test (a real git repo)
    heldout/<task>/           # hidden tests, never enter a workspace
    harnesses/baseline/ candidate/
    tasks/*.yaml  eval.yaml
  runs/2026-xx-xx-demo/       # COMMITTED sample run + rendered report
  tests/                      # pytest for the evaluator itself
```

**Config shape**

```yaml
repo: examples/demo-repo
harnesses:
  baseline:
    command: claude -p "{prompt}" --output-format json --model {model}
    model: claude-sonnet-5
    instructions: null
  candidate:
    command: claude -p "{prompt}" --output-format json --model {model}
    model: claude-sonnet-5
    instructions: examples/harnesses/candidate/AGENTS.md
reps: 2
timeout_s: 600
tasks: [add-retry, fix-rounding, refactor-config, add-cli-flag]
graders:
  - {id: acceptance,  command: "pytest -q tests/acceptance", critical: true,  dimension: correctness}
  - {id: heldout,     command: "pytest -q tests/heldout",    critical: true,  dimension: fidelity, overlay: heldout}
  - {id: regressions, command: "pytest -q",                  critical: true,  dimension: regression}
  - {id: lint,        command: "ruff check .",               critical: false, dimension: conventions}
  - {id: types,       command: "mypy src",                   critical: false, dimension: conventions}
```

Adding a task, grader, or harness must require **zero evaluator code changes**. This is also what makes the 90-minute live session survivable.

**Comparator rules, deterministic, and printed verbatim in the report:**

```
task outcome (per harness) = PASS     iff all critical graders pass in ALL reps
                             FAIL     iff all critical graders fail in ALL reps
                             UNSTABLE otherwise
transition = baseline_outcome -> candidate_outcome

recommendation:
  any PASS -> FAIL                         -> NEGATIVE
  candidate PASS count < baseline          -> NEGATIVE
  improvements == 0 and cost delta > +25%  -> NEGATIVE
  improvements > 0 and regressions == 0    -> POSITIVE SIGNAL
  otherwise                                -> INCONCLUSIVE

confidence: LOW if reps < 2 or any task UNSTABLE, else MODERATE. Never HIGH at n=4.
```

UNSTABLE tasks are excluded from improvement/regression counts and listed in their own section. Cost deltas are computed over successful trials only, and the report says so on the line where the number appears.

**Parallelism:** `--jobs N` exists but defaults to 1. When `N>1` the report prints a banner that wall-clock figures are unreliable for that run. (The brief cut parallelism; keeping it as an escape hatch with an honest caveat is cheaper than blowing the budget.)

---

## 5. Cost and wall-clock budget

16 trials x ~3-5 min = **50-80 minutes of wall clock**, plus retries. Estimated spend **$2-8**.

Consequence baked into the schedule: **the full run launches at ~T+4:30 and executes in the background** while the report layer and docs are written. If it is not launched by T+5:00, cut to 3 tasks immediately.

---

## 6. Demo repo and tasks

Small Python package with `ruff` + `mypy` + `pytest` configured. Four tasks, each loading a different dimension:

| Task | Exercises | Design note |
|---|---|---|
| `add-retry` | Correctness | Visible tests are adequate. Control task. |
| `fix-rounding` | **Fidelity** | Visible test asserts one value only; held-out tests cover negatives and half-even rounding. **Deliberate "passes but wrong" trap.** |
| `refactor-config` | Regression safety | Touches shared code; the full suite catches breakage. |
| `add-cli-flag` | Conventions | Repo convention (docstring + type hints + docs entry) is encoded in the candidate `AGENTS.md` only. |

Expected result shape: candidate improves Conventions and possibly Regression safety, and costs more. "Better but more expensive" is a more useful report than a clean win, and it is exactly the trade-off a single score would hide.

**Committed sample run.** `runs/<id>/` and its rendered `report.md` are committed. A reviewer with no agent CLI and no API key runs `harness-eval report runs/<id>` and sees the real report in under a minute. This is what makes the five-minute README promise actually hold.

---

## 7. Deliverable 5: process capture (starts at T+0, not at the end)

The requirement asks for *"what you asked, what you checked by hand, and where the agent was wrong."*

- `AGENTS.md`: the instructions given to the agent building this tool.
- `prompts/NN-*.md`: each substantive prompt, verbatim, in order.
- `transcripts/`: export at least one **complete** session. The source already exists: `~/.claude/projects/c--Users-HP-Desktop-Take-Home/<session>.jsonl`. Copy it and render a readable markdown version; do not trim it.
- `NOTES.md`: append an entry **at the moment it happens**, timestamped:
  - what was checked by hand, and what was found
  - every case where the agent produced something wrong, and the correction

`NOTES.md` is unrecoverable if left to the end. It is also where the §8 distrust case comes from.

---

## 8. `DESIGN.md`: one page, hard limit

Four sections, written **last**, when the distrust case is real:

1. **Concepts and why** (~6 lines), the table in §2, plus one line on adopting Anthropic's vocabulary rather than reinventing it.
2. **Five hardest decisions**, final five chosen after the build, from:
   - paired Δ over an absolute score, and refusing any composite number
   - held-out tests as a first-class grader (cost: task-authoring time; benefit: catches "passed but wrong")
   - fresh-copy isolation over `git worktree` (hook non-firing + history leakage)
   - `run`/`report` split so evidence outlives the render
   - deterministic printed recommendation rule, and refusing HIGH confidence at n=4
   - treating UNSTABLE as an outcome rather than rounding it to PASS or FAIL
3. **What was cut and why**, dashboard, parallel-by-default, second agent SDK, LLM judge, composite score, significance testing, Docker. Frame as *"chose not to spend budget here"*, never *"ran out of time."*
4. **The distrust case**, one grounded paragraph. **Do not pre-write this.** Likely sources, in order: (a) `fix-rounding` passes `acceptance` and fails `heldout`; (b) a task returns different outcomes across reps and the first comparator draft silently rounded it to PASS; (c) a cost delta that turns out to be a timeout, not efficiency.

---

## 9. Schedule

| Time | Block | Gate |
|---|---|---|
| 0:00-0:30 | Install + auth Claude Code CLI. Verify every flag, record in `NOTES.md`. Create venv. **Start process capture.** | `claude -p "hi" --output-format json` returns JSON |
| 0:30-0:50 | Demo repo v0 + 1 task, minimal (just enough to smoke-test |) |
| 0:50-1:40 | pydantic models, YAML loader, `validate`, CLI skeleton | `harness-eval validate eval.yaml` passes |
| 1:40-2:50 | Workspace isolation, `ShellAgentAdapter`, evidence collection | **Gate: one real trial end-to-end produces `patch.diff` + cost** |
| 2:50-3:30 | `CommandGrader`, critical flag, held-out overlay, grader logs | Graders produce logs on the smoke trial |
| 3:30-4:00 | Comparator: transitions, dimensions, flakiness, recommendation rule + unit tests | `pytest` green on the evaluator |
| 4:00-4:30 | Demo repo -> 4 tasks + held-out tests + baseline/candidate harness dirs |, |
| **4:30** | **Launch full run in background (16 trials)** | **Hard gate, if not launched by 5:00, cut to 3 tasks** |
| 4:30-5:30 | Report layer: `report.md`, `report.json`, per-task pages, evidence links | Renders from a partial run |
| 5:30-6:00 | **Read 2-3 patches by hand.** Compare against grader verdicts. Log findings in `NOTES.md` | Where the distrust case comes from, do not skip |
| 6:00-6:30 | Fix what hand inspection revealed. Re-render (no re-run) |, |
| 6:30-7:00 | README, commit the sample run, verify on a clean checkout | **Gate: <5 min from clone to rendered report** |
| 7:00-7:30 | `DESIGN.md` one-pager | Fits on one page |
| 7:30-8:00 | `PROCESS.md`, transcript export, prompts, final pass |, |

**Degradation ladder, in order, if behind:** 4 tasks -> 3; reps 2 -> 1 on two tasks (report "reliability measured on 2 tasks only"); drop the `types` grader; per-task pages become sections in `report.md`. Never cut: the hand-inspection block, `DESIGN.md`, or the process capture.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| CLI flags differ from the brief's table | Verified at T+0:30, before any design depends on them |
| CLI auth fails / no API credit | Discovered at T+0:30, not T+4:30 |
| Agent runs slower than 5 min/trial | `--jobs 2` with the wall-clock caveat banner, or cut to 3 tasks |
| Candidate shows no effect at all | Still a valid, reportable result, "no detectable difference at n=4" is honest, and the tool is what's being graded |
| Everything passes in both arms | The `fix-rounding` held-out trap is designed to prevent this |
| Windows path/quoting bugs in grader commands | Smoke-tested at the 1:40 gate, before any task authoring |

---

## 11. Definition of done

- [ ] `harness-eval evaluate examples/eval.yaml` runs end-to-end against the real Claude Code CLI
- [ ] `report.md` + `report.json`; every aggregate claim links to a task, patch, and grader log
- [ ] `harness-eval report runs/<id>` renders the committed sample run with no CLI and no spend
- [ ] README: clone -> rendered report in under 5 minutes, verified on a clean checkout
- [ ] `DESIGN.md`: concepts / five hardest decisions / cuts / distrust case, one page, hard limit
- [ ] `AGENTS.md`, `prompts/`, one complete transcript, `NOTES.md` with hand-checks and agent errors
- [ ] Adding a task or grader requires editing YAML only, demonstrable live

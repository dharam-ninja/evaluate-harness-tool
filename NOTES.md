# Working log

Append an entry **at the moment it happens**. This file cannot be reconstructed afterwards,
and it is the source for DESIGN.md §4 and PROCESS.md.

Format: `## [T+H:MM] <what happened>` then, what I checked by hand / what I found /
what the agent got wrong / what I changed.

---

## [T+0:00] Phase 0: ground truth

### Environment

| Item | Value |
|---|---|
| OS | Windows 11 Home Single Language, 10.0.26200 |
| Shell | PowerShell 5.1 (primary), git-bash available |
| Python | 3.10.4 (`C:\Users\HP\AppData\Local\Programs\Python\Python310`) |
| git | 2.52.0.windows.1 |
| node / npm | v24.13.1 / 11.16.0 |
| Claude Code CLI | **2.1.272**, `C:\Users\HP\AppData\Roaming\npm\claude.ps1` |
| codex CLI | not installed (single-adapter decision, PLAN.md §0) |

Install note: `npm install -g @anthropic-ai/claude-code` succeeded but npm **blocked the
postinstall script** (`node install.cjs`) pending `npm approve-scripts`. The CLI works
anyway, `claude --version` returns `2.1.272 (Claude Code)` in PowerShell. Not chased
further; recorded in case a native-build feature turns out to be missing later.

Auth: **already authenticated** via the OAuth session shared with the VSCode extension.
No API key set. This matters, see the `--bare` finding below.

### Flag audit: `claude --help`, v2.1.272

PLAN.md §3 lists these as asserted by the brief and unverified. Verdicts:

| Flag | Verdict | Exact help text / note |
|---|---|---|
| `-p` | **CONFIRMED** | `-p, --print`, "Print response and exit" |
| `--output-format json` | **CONFIRMED** | choices `text`, `json`, `stream-json`; "only works with --print" |
| `--model` | **CONFIRMED** | takes an alias (`fable`, `opus`, `sonnet`) or a full name (`claude-fable-5`) |
| `--add-dir` | **CONFIRMED** | `<directories...>` |
| `--settings` | **CONFIRMED** | path to a settings JSON file **or a JSON string** |
| `--bare` | **CONFIRMED but unusable here** | see below |
| `--no-session-persistence` | **CONFIRMED** | "only works with --print" |
| `--max-budget-usd` | **CONFIRMED** | `<amount>`, "only works with --print" |
| `--fallback-model` | **CONFIRMED** | accepts a comma-separated list |

All nine exist. The brief's *descriptions* were not all accurate, see §Falsified below.

### Flags the brief never mentioned that change the design

| Flag | Why it matters |
|---|---|
| `--permission-mode <acceptEdits\|auto\|bypassPermissions\|manual\|dontAsk\|plan>` | **Blocking.** A headless agent that must edit files needs this. |
| `--permission-prompts <host\|none>` | `none` = "anything that would prompt is denied automatically". Needed so a trial fails fast instead of hanging. |
| `--safe-mode` | Disables CLAUDE.md, skills, plugins, hooks, MCP, commands, agents, **but keeps auth working normally**. This is what the brief thought `--bare` was. |
| `--setting-sources user,project,local` | Controls which settings files load. The real lever for config isolation between arms. |
| `--strict-mcp-config` | Only use MCP servers from `--mcp-config`. The clean way to run the MCP scenario. |
| `--effort <low..max>` | Another harness dimension, free to compare. |
| `--system-prompt` / `--append-system-prompt` | Another harness dimension. |
| `--session-id <uuid>` | Deterministic session ids, useful for naming trial artifacts. |
| `--tools` / `--allowedTools` / `--disallowedTools` | Tool-surface is a harness dimension too. |

### Live call: `claude -p "reply with the word ok" --output-format json`

Raw response, verbatim:

```json
{"duration_api_ms":2953,"stop_reason":"end_turn","session_id":"ad977d16-cd34-4d9c-99ac-a306a0de8674","total_cost_usd":0.09233250000000001,"usage":{"input_tokens":2,"cache_creation_input_tokens":7548,"cache_read_input_tokens":31561,"output_tokens":4,"output_tokens_details":{"thinking_tokens":0},"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":7548,"ephemeral_5m_input_tokens":0},"inference_geo":"not_available","iterations":[{"input_tokens":2,"output_tokens":4,"cache_read_input_tokens":31561,"cache_creation_input_tokens":7548,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":7548},"type":"message"}],"speed":"standard"},"modelUsage":{"claude-haiku-4-5-20251001":{"inputTokens":897,"outputTokens":13,"cacheReadInputTokens":0,"cacheCreationInputTokens":0,"webSearchRequests":0,"costUSD":0.000962,"contextWindow":200000,"maxOutputTokens":32000,"thinkingTokens":0,"canonicalModel":"claude-haiku-4-5","provider":"firstParty","costBasis":"list"},"claude-opus-5[1m]":{"inputTokens":2,"outputTokens":4,"cacheReadInputTokens":31561,"cacheCreationInputTokens":7548,"webSearchRequests":0,"costUSD":0.09137050000000001,"contextWindow":1000000,"maxOutputTokens":64000,"thinkingTokens":0,"canonicalModel":"claude-opus-5","provider":"firstParty","costBasis":"list"}},"permission_denials":[],"terminal_reason":"completed","fast_mode_state":"off","fast_mode_disabled_reason":"extra_usage_disabled","subagent_stats":{"spawned":0,"requested":{"background":0,"foreground":0,"unset":0},"started_in_background":0,"max_depth":0,"spawned_by_subagents":0,"completed":0,"failed":0,"killed":{"parent":0,"user":0,"system":0},"refused":{"depth_limit":0,"concurrency_limit":0,"budget":0},"by_type":{}},"is_error":false,"num_turns":1,"subtype":"success","api_error_status":null,"result":"ok","ttft_ms":2528,"type":"result","duration_ms":2592,"uuid":"b3e749af-8d35-428b-b152-3380a390131e","ttft_stream_ms":2525,"time_to_request_ms":640,"first_content_frame_ms":2526,"queued_turn_count":0,"result_index":0}
```

### Field map for `evidence.py`

| Evidence | JSON path | Note |
|---|---|---|
| cost | `total_cost_usd` | float USD. **Includes cache-read cost and side-model calls.** |
| per-model cost | `modelUsage.<model>.costUSD` | **camelCase**, unlike the top-level snake_case |
| tokens in/out | `usage.input_tokens` / `usage.output_tokens` | |
| cache tokens | `usage.cache_creation_input_tokens` / `usage.cache_read_input_tokens` | dominates cost here |
| turns | `num_turns` | |
| duration (total) | `duration_ms` | |
| duration (API only) | `duration_api_ms` | |
| error flag | `is_error` (bool), `subtype` (`success`), `terminal_reason` (`completed`) | three overlapping signals; prefer `is_error` + `subtype` |
| API error | `api_error_status` | `null` on success |
| **permission denials** | `permission_denials` | array. **Must be captured**, see below |
| agent's answer | `result` | |
| session id | `session_id`, `uuid` | |
| subagents | `subagent_stats.spawned` etc. | |

### Timing

Wall clock **4.9 s**; `duration_ms` 2592; `time_to_request_ms` 640.
-> CLI process startup overhead ≈ **2.3 s per trial**. Negligible against a 3-5 min task.

**This does NOT validate PLAN.md §5's 3-5 min/trial estimate.** It was a no-tool text reply.
The real per-trial figure has to be measured at the Phase 3 gate, and the §5 wall-clock
budget stays provisional until then.

### Packaging

`python -m venv .venv` + `pip install -e ".[dev]"` clean. `harness-eval --help` fails with:

```
ImportError: cannot import name 'app' from 'harness_eval.cli'
```

Correct gate result, entry point wiring is sound, only the stub is missing.

---

## [T+0:30] Falsified assumptions: things PLAN.md / the brief got wrong

**1. `--bare` is unusable on this machine.** Help text: *"Anthropic auth is strictly
ANTHROPIC_API_KEY or apiKeyHelper via --settings (OAuth and keychain are never read)."*
This machine authenticates by OAuth, so `--bare` runs would fail to authenticate.

**2. The brief mis-describes `--bare`.** It claimed `--bare` "skips hooks, skills, MCP
servers, subagents, plugins, auto-memory, and CLAUDE.md discovery." Actual text: skips
"hooks, LSP, plugin sync, attribution, auto-memory, background prefetches, keychain reads,
and CLAUDE.md auto-discovery", and explicitly *"Skills still resolve via /skill-name."*
No mention of MCP servers. **`--safe-mode` is the flag the brief was describing**, and it
keeps auth working. The brief's §6.2 warning ("you cannot use --bare to compare hook-present
vs hook-absent") still holds, and applies to `--safe-mode` too.

**3. Cost is contaminated by ambient config, the most important finding.**
That trivial "ok" reply cost **$0.092**. Breakdown: `cache_read_input_tokens: 31561`,
and `modelUsage` shows it ran on **`claude-opus-5[1m]`** ($0.0914) plus a `claude-haiku-4-5`
side-call ($0.0010). Nobody asked for Opus; it was inherited from this machine's ambient
config.

Consequences for the design:
- Every trial **must** pin `--model` explicitly. An unpinned arm measures the machine, not
  the harness.
- Trials must control `--setting-sources` so the operator's own settings do not leak into
  either arm.
- `total_cost_usd` includes cache-read cost. Two arms run back-to-back share cache state,
  so the second arm can look cheaper for reasons that have nothing to do with the harness.
  The report must say this next to the cost number, and PLAN.md §4's "successful trials
  only" caveat is **not sufficient on its own**.
- `total_cost_usd` also aggregates side-model and subagent spend, which is correct for
  "what did this cost" but means cost is not proportional to the main model's token count.

**4. PLAN.md's `eval.yaml` command template is broken.** It is:
`claude -p "{prompt}" --output-format json --model {model}`, with no permission handling.
Real tasks require file edits; without `--permission-mode` the trial is denied or hangs, so
**every trial in Phase 6 would have failed at the gate.** Corrected template:

```
claude -p "{prompt}" --output-format json --model {model} \
  --permission-mode acceptEdits --permission-prompts none \
  --no-session-persistence --setting-sources project \
  --max-budget-usd {budget}
```

`--permission-prompts none` is deliberate: anything needing a prompt is denied rather than
hanging, and `permission_denials` in the envelope then tells us it happened. A trial with a
non-empty `permission_denials` array is **not** a clean failure; it is a blocked trial and
the comparator must treat it separately, or a harness that merely triggers more prompts will
look worse on correctness.

**5. `permission_denials` must be first-class evidence.** Not in PLAN.md at all. Without it,
a blocked trial is indistinguishable from an agent that tried and failed, and it is cheap,
so it would also drag the cost average down and make the blocked arm look *efficient*.

### Corrected template: validated live

Ran the full corrected template end to end. Result:

```
ELAPSED: 7.97s
is_error       : False
result         : ok
total_cost_usd : 0.05077
num_turns      : 1
models used    : claude-haiku-4-5-20251001, claude-sonnet-5
denials        : 0
```

- `claude-sonnet-5` **is** a valid model id (PLAN.md's `eval.yaml` guess was right).
- All six added flags are accepted together; `--setting-sources project` does not error.
- Pinning the model dropped cost $0.092 -> $0.051 on an identical prompt. That difference
  was pure ambient-config contamination.

**6. There is a fixed per-trial cost floor of roughly $0.05.** Even a 2-token prompt costs
that, from cache creation plus an unavoidable `claude-haiku-4-5` side-call that appears in
`modelUsage` regardless of `--model`. Implications:
- ~$0.80 of the 16-trial run is fixed overhead unrelated to any task.
- It is roughly equal across arms, so the **paired cost delta stays meaningful**: which is
  what the tool reports. Absolute per-task cost is not a meaningful number and the report
  should not present one as though it were.
- `modelUsage` must be recorded per trial, not just `total_cost_usd`, so the report can show
  main-model cost separately from side-model overhead.

Startup overhead measured twice: 4.9s and 8.0s wall for ~2.6s of API time, so **2-5 s of
process overhead per trial**. Still negligible at task scale.

### Changes to make before Phase 2

- [ ] `examples/eval.yaml`: adopt the corrected command template above
- [ ] `models.py`: add `permission_denials` and `TIMEOUT`/`BLOCKED` as distinct outcomes
- [ ] `evidence.py`: parse the field map above; absent field -> `null`, never `0`;
      record the whole `modelUsage` block, not just `total_cost_usd`
- [ ] `report.py`: cost caveat must mention prompt-cache sharing and the ~$0.05 fixed floor,
      not just "successful trials only"; report paired deltas, never absolute per-task cost
- [ ] PLAN.md §5: mark the 3-5 min/trial budget provisional until the Phase 3 gate measures it

---

## [T+0:50] Phase 1: demo repo + the fix-rounding trap

### Structural correction: acceptance tests are per-task, not part of the repo

PLAN.md put acceptance tests in `demo-repo/tests/acceptance/`. That cannot work once four
tasks exist: all four task's acceptance suites would sit in the base repo at once, three of
them failing during every trial of the fourth. It also contradicts the requirement that the
unmodified repo be green.

Corrected layout, acceptance is now symmetric with held-out, both overlaid per trial:

```
examples/demo-repo/tests/regression/   pre-existing suite. Green. Ships in the repo.
examples/tasks/<task>/acceptance/      visible to the agent. Copied in BEFORE the run.
examples/heldout/<task>/               never visible.        Copied in AFTER the run.
```

### Second correction: the regression grader command was wrong

PLAN.md's regression grader was a bare `pytest -q`. With overlays in place that also
collects `tests/acceptance` and `tests/heldout`, so **a task the agent simply failed would
also register as a regression**, collapsing three dimensions the tool exists to keep apart.
Changed to `pytest -q tests/regression`. Fixed in `examples/eval.yaml`.

### The task

`round_money` currently truncates toward zero (`int(amount * 100) / 100`). The ticket in
`examples/tasks/fix-rounding.yaml` states the full rule, 2 dp, half-way moves away from
zero, negatives follow the same rule, and names no implementation.

Acceptance (visible) asserts only 2.344 -> 2.34, 2.346 -> 2.35, 19.99 -> 19.99. Every value is
clearly off the midpoint, so `round(amount, 2)` satisfies all three.
Held-out asserts the half-way values 0.125 / 0.625 / 1.125 and their negatives, all exactly
representable in binary so a failure is a real rounding-mode difference, not a float artefact.

### Verified by hand: truth table

Built a scratch workspace with both overlays and ran all five graders against three states:

| State of `round_money` | regression | acceptance | held-out | ruff | mypy |
|---|---|---|---|---|---|
| 1. unmodified (truncates) | 5 pass | **2 fail**, 1 pass | **4 fail** | pass | pass |
| 2. naive `round(amount, 2)` | 5 pass | **3 pass** | **3 fail**, 1 pass | pass | pass |
| 3. `Decimal` + `ROUND_HALF_UP` | 5 pass | 3 pass | **4 pass** | pass | pass |

**The trap fires.** State 2 is the case the tool exists to catch: acceptance green, held-out
red on `assert 0.12 == 0.13`. Python's `round` is half-to-even; the ticket asked for
half-away-from-zero.

The line that matters most in that table is state 2's **ruff pass / mypy pass**. The naive
fix is clean, typed, lints, and satisfies every visible test. `mypy` is `strict = true` and
still says nothing. **Held-out is the only grader in the whole suite that catches it**, which
is the concrete demonstration that a passing suite is not proof of correct behaviour, measured
rather than asserted.

Also confirmed: state 3 leaves the regression suite green, so a correct fix does not trip a
false regression through `sum_line_items`, which calls `round_money`.

### Unmodified source repo

```
pytest -q          5 passed in 0.05s
ruff check .       All checks passed!
mypy src           Success: no issues found in 5 source files
```

Baseline is clean. Scratch workspace deleted.

### Note for Phase 3

`pythonpath = ["src"]` in the demo repo's pytest config, so no `pip install -e .` is needed
inside a trial workspace. Saves ~20 s and one failure mode per trial.

---

## [T+1:40] Phase 3: runner. Gate met.

Phase 2 was skipped in the sequence, so `models.py`, `config.py` and `cli.py` were built
here first; `run` cannot be wired without them.

### Gate

```
run smoke-01  1 trials
  running fix-rounding/baseline/0 ...
    completed   46.2s  $0.2971  1 file(s)  840B patch
```

`runs/smoke-01/trials/fix-rounding/baseline/0/` holds `patch.diff` (840 B), `result.json`
with `total_cost_usd = 0.2971216`, plus `transcript.json`, `command.txt`, `prompt.txt`,
`agent_stdout.txt`, `agent_stderr.txt`.

### Checked by hand: the patch

Read `patch.diff` in full. It contains exactly one hunk in `src/demo/money.py`: the import
of `Decimal, ROUND_HALF_UP`, a docstring stating the rule, and

```python
-    return int(amount * 100) / 100
+    return float(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
```

That matches the workspace on disk. Nothing missing, nothing spurious.

New files were not exercised by this trial (1 modified file, 0 created), so I verified that
path separately: built a workspace, modified one file, created `rounding_helpers.py`, deleted
`retry.py`. `changed_files` returned all three and the patch carried both a `new file mode`
and a `deleted file mode` header. The untracked-file path works.

### Finding 1: the baseline solved it correctly, with no AGENTS.md

I expected the trap to catch a naive `round(amount, 2)`. It did not: Sonnet read the ticket,
which states the half-way and negative rules in full, and implemented them. Graded by hand:

| grader | result |
|---|---|
| regression | 5 passed |
| acceptance | 3 passed |
| **held-out** | **4 passed** |
| **lint** | **FAIL, I001 import block un-sorted** |
| types | Success |

So the honest read is: **the trap is a detector, not a guarantee the agent falls in.** The
task is fair by construction (§Phase 1), and a capable model on a well-written ticket passes
it. If both arms keep passing `fix-rounding`, the report must say "no divergence observed on
fidelity" rather than implying the dimension found something.

That is a limitation of the *task suite*, not of the tool, and it is worth stating plainly
in DESIGN.md: a four-task suite of tractable tasks may simply not discriminate. Phase 6 should
add at least one task where the ticket is realistically underspecified.

### Finding 2: the conventions dimension fired on the first real trial

`ruff` flagged `I001` on the agent's own import line: it wrote
`from decimal import Decimal, ROUND_HALF_UP` where the repo's lint wants them sorted. The
demo repo was lint-clean before the agent touched it.

This is the multi-dimensional result the tool exists to produce, and it arrived unprompted:
**correct, verified against held-out tests, and still in violation of the repo's conventions.**
A single pass/fail signal would have reported this trial as a clean win.

### Finding 3: the agent was denied the ability to run tests

`permission_denials` is not empty:

```json
{"tool_name": "Bash",
 "tool_input": {"command": "... python -m pytest tests/acceptance/test_rounding.py -q"}}
```

`--permission-mode acceptEdits` with `--permission-prompts none` (set in Phase 0) lets the
agent edit files but denies Bash, so it could not verify its own work. It got the answer right
anyway, but this is a **threat to the experiment's validity**, not a cosmetic issue:

- the candidate `AGENTS.md` is meant to say something like "run the full test suite before
  finishing". Under the current permissions that instruction is unfollowable, so the change
  under test is partly neutered before it is measured.
- both arms are handicapped identically, so the *paired* comparison is still sound. It is the
  realism that suffers.

Three options, needs a decision before Phase 6:
1. keep `acceptEdits`, safe, both arms equally limited, candidate's "run the tests"
   instruction cannot take effect
2. `--permission-mode bypassPermissions`, realistic, but arbitrary command execution on this
   machine with no container
3. **targeted allowlist**, e.g. `--allowedTools "Bash(python -m pytest*)" Read Edit Write Glob Grep`,
   which lets the agent verify without granting a general shell

Recommending 3. Logged rather than decided unilaterally, because it changes what the eval
measures.

The `BLOCKED` status logic behaved correctly here: denials were present but the patch was
non-empty, so the trial is `completed`, not `blocked`. BLOCKED fires only on denials *and* an
empty patch, a trial that was stopped and produced nothing, which would otherwise read as a
fast, cheap, efficient failure.

### Finding 4: wall-clock budget is better than planned

46.2 s for a real single-file task, against PLAN.md §5's 3-5 min estimate. If that holds, 16
trials is ~15-25 min rather than 50-80. The §5 budget stays provisional until a multi-file
task (`refactor-config`) is measured in Phase 6, but the schedule has slack it did not assume.

Cost: $0.2971 for this trial against the ~$0.05 floor from Phase 0, so the floor is a small
fraction of a real task. Spend estimate for 16 trials ≈ $4-5.

### Decisions made while building

- **Prompt goes in on stdin, not interpolated into the command line.** Task prompts are
  multi-line; embedding one in a Windows shell command is a quoting minefield and a mangled
  prompt would look exactly like an agent failure. `{prompt}` in a template is still honoured
  and stripped, so the config stays as PLAN.md described it.
- **Process-tree kill on timeout.** `Popen.kill()` reaches only the shell; the agent is a
  node grandchild. An orphan would hold the workspace open and corrupt the next trial, so
  timeouts go through `taskkill /F /T`.
- **Acceptance overlay lands before the initial commit**, so the agent may read and run those
  tests but they never appear in its patch as work it did.
- **Workspaces are kept** under `runs/<id>/workspaces/` rather than a system temp dir. They
  are gitignored, and Phase 8 needs to read them by hand.
- Evaluator's own `ruff` and `mypy` are green. `B008` is ignored project-wide (typer's API
  requires calls in argument defaults); the two blind `except` clauses carry targeted `noqa`
  with the reason, since both are deliberate, a broken trial must not abort a run that costs
  money.

---

## [T+2:20] Phase 2 gap-closing: audited and completed

Audited Phase 2 against its own prompt after the fact. It was ~60% done. Four real gaps,
all closed before starting Phase 4.

**1. The domain vocabulary had drifted.** I had written `TaskSpec`, `HarnessSpec`,
`GraderSpec`, `TrialResult`. PLAN.md §2 and the phase prompt both say `Task`,
`AgentHarness`, `Grader`, `Trial`, and those names go into DESIGN.md §1 where reviewers
compare vocabulary. Renamed across all six modules. Cheap now; it would have been spread
through the comparator and report templates by Phase 7.

**2. `TaskComparison` and `EvaluationReport` did not exist.** Phase 5 and Phase 7 both build
on them, so they would have been invented ad hoc there instead of being the agreed model.
Added, along with `DimensionSummary` and `CostSummary`. `CostSummary` carries its own
`caveats` list rather than leaving them to a template, so the number and the reason it needs
qualifying cannot drift apart.

**3. Unknown grader dimensions were not rejected.** There is a genuine tension in the Phase 2
prompt: *"unknown dimension rejected"* versus *"do not hardcode a dimension name in Python."*
Resolved by having the config declare its own vocabulary -- `dimensions:` in `eval.yaml` --
and validating graders against that list. Python enforces consistency without knowing the
names, so adding a grader stays a YAML-only edit. Also added duplicate-grader-id rejection.

The four declared dimensions map 1:1 onto the assignment's four quality claims, which is
worth stating in the report: correctness / fidelity / regression / conventions.

**4. `tests/test_config.py` was never written** -- half the Phase 2 gate. Now 13 tests.

Also wired `evaluate` = run then report, by extracting the run loop into `_execute()` so
`run` and `evaluate` share it. `report` and `evaluate` both funnel through `_render()`, which
raises `NotImplementedError` until Phase 7.

### Caught while writing the tests

First draft of the test fixture copied `eval.yaml` into `tmp_path` and mutated it, but did
not copy the directories it references. Three tests passed for the wrong reason: the
"instructions -> AGENTS.md not found" error fired before the mutation under test was ever
reached. A test that asserts only `pytest.raises(ConfigError)` would have stayed green
forever while checking nothing.

Fixed by rewriting every path in the copied config to an absolute path back into the real
repo, so the mutation under test is the only difference. Worth remembering for Phase 5's
comparator tests: `raises(SomeError)` without matching the message is not a test.

### Phase 2 gate: one part is unmeetable, and that is my plan's fault

The gate says `validate` prints `4 x 2 x 2 = 16 trials`. But Phase 6 is what creates three of
those four tasks, so with only `fix-rounding` in place the honest output is `1 x 2 x 2 = 4`.
The gate should have read "prints the trial matrix it would run", not a fixed number. Noted
rather than papered over; the matrix printing itself works.

State after this pass: `ruff` clean, `mypy` clean on 11 files, 13 tests green, and the
baseline/candidate arms verified to differ (AGENTS.md absent vs present) without spending an
agent call.

---

## [T+2:40] Phase 3 open issues: reviewed, two fixed, two decided

### The cost dimension had a systematic bias toward the candidate

Measured from the smoke trial's envelope:

| | tokens | approx. share of cost |
|---|---|---|
| cache **creation** | 53,061 | ~67% |
| cache **read** | 304,813 | ~31% |
| output | 2,276 | ~11% |
| real input | 14 | ~0 |

Cost is almost entirely prompt-cache mechanics, and cache creation is priced roughly an order
of magnitude above cache read. So the arm that runs **first** pays to build the cache and the
arm that runs **next** free-rides on it.

The run loop was `for task -> for harness -> for rep`, so baseline always ran first and
candidate always second. **The candidate would have looked cheaper on every task for reasons
that have nothing to do with the harness change**, and efficiency is one of the four
dimensions the report states. That is a wrong number in a predictable direction, favouring
whatever is being proposed, which is the worst possible direction for a tool meant to be
trusted before a rollout.

Fixed: the loop is now `for task -> for rep -> for harness`, with the arm order reversed on
odd reps. Each arm goes first equally often, so the discount cancels across reps.

Not yet quantified, the arms do not share a full cache prefix (the candidate injects
AGENTS.md, which changes the context), so the effect is partial. Phase 6 should run one arm
twice back-to-back and compare rep 0 against rep 1; that isolates the magnitude in a single
trial pair. Until then the report must carry the mechanism as a caveat next to the number,
not just "successful trials only".

### Permissions: decided: targeted allowlist

Added `--allowedTools "Bash(python -m pytest*)" Read Edit Write Glob Grep` to the command
template. The agent can now verify its own work without being handed a general shell.

This matters because the candidate `AGENTS.md` is meant to carry an instruction like "run the
full suite before finishing". Under the previous permissions that instruction was physically
unfollowable, so the experiment would have measured "no signal" when the truthful answer was
"we prevented the mechanism from operating."

### Infrastructure errors: decided: exclude and report separately

`TrialStatus.ERROR` trials will not feed the PASS/FAIL/UNSTABLE outcome. The report carries an
explicit "N trials excluded for infrastructure reasons" section listing each one.

Rationale: UNSTABLE must mean *the agent was inconsistent*, not *the API blipped*. Retrying
would hide the rate; counting as FAIL would turn a network blip during the candidate's run
into a `PASS -> FAIL` regression, which is the single most prominent thing the report shows.
To implement in Phase 5.

### Still open, deliberately deferred

- **Untested failure paths.** `TrialStatus.TIMEOUT` and the `taskkill /F /T` tree kill have
  never fired. Covering both in Phase 4's `tests/test_graders.py`, where a sleeping command
  makes the timeout path cheap to exercise.
- **Budget exhaustion is unexplored.** Unknown whether hitting `--max-budget-usd` yields a
  clean error envelope or a partial patch marked `completed`. A partial patch reported as
  `completed` would be graded as a genuine agent failure. One deliberate trial at
  `--max-budget-usd 0.01` in Phase 6 settles it.
- **Suite discriminating power.** The baseline solved `fix-rounding` correctly including
  held-out. If that repeats across four tasks every transition is PASS->PASS and the honest
  output is "no detectable difference at n=4". Tempting to fix by writing a vague ticket;
  that is exactly the self-deception the assignment warns about. Phase 6 keeps the tickets
  fair. Note that the only real signal so far came from **conventions** (I001), not
  correctness, which is probably where an AGENTS.md change actually shows up, and argues for
  weighting the suite toward convention-sensitive tasks.
- **stdin prompt delivery is untested against Codex**, which takes the prompt as a positional
  argument. The agent-agnostic claim is currently theoretical and should be stated that way
  in DESIGN.md rather than asserted.
- **Phase 9 must commit `trials/` but not `workspaces/`**: workspaces are full repo copies.

---

## [T+3:20] Phase 4: graders and the held-out overlay. Gate met.

```
completed  34.2s  $0.1453  1 file(s)  856B  acceptance heldout regressions lint types
```

Five grader logs in `runs/smoke-02/trials/fix-rounding/baseline/0/graders/`. Checked by hand:
`heldout.log` shows `pytest -q tests/heldout` -> `4 passed`, and `patch.diff` contains **zero**
occurrences of "heldout" and touches only `src/demo/money.py`. The overlay landed after the
patch was taken, as intended.

### The bug that would have poisoned an entire dimension

`tests/test_graders.py` failed on a lint assertion. I assumed the held-out overlay was
polluting `ruff check .`. It was not. The real cause:

```
ruff check .   exit=1  'ruff' is not recognized as an internal or external command
mypy src       exit=1  'mypy' is not recognized as an internal or external command
pytest -q      exit=2  (resolved to the SYSTEM python's pytest, not the venv's)
```

Grader subprocesses inherited `os.environ` but **not the evaluator's venv**, so `ruff` and
`mypy` did not resolve at all. They exit 1 with empty stdout -- which my grader maps to
`FAIL`, identically to a real lint failure.

**Every `lint` and `types` grader would have reported FAIL on every trial, in both arms.**
Both are non-critical, so nothing would have blocked; the report would simply have stated
"lint-clean 0/4 -> 0/4" with total confidence. A symmetric wrong number is the worst kind,
because the delta looks correct and the absolute is nonsense. Nothing in the run output would
have hinted at it.

Fixed in `run_shell`: the evaluator's interpreter directory goes first on `PATH`. That also
makes bare `python` mean the venv's interpreter for both graders and the agent, so they see
the same pytest.

Worth carrying into Phase 8: **a grader that cannot run and a grader that fails look
identical through an exit code.** Anywhere else that maps exit codes to verdicts deserves the
same suspicion.

### Conventions turned out to be non-deterministic

smoke-01 and smoke-02 are the same task, same arm, same model. The patches differ:

```
smoke-01:  from decimal import Decimal, ROUND_HALF_UP     -> ruff I001  FAIL
smoke-02:  from decimal import ROUND_HALF_UP, Decimal     -> ruff       PASS
```

Same harness, opposite conventions verdicts. So the `I001` finding I recorded in Phase 3 as
"the conventions dimension fired" is **run-to-run noise, not a property of the baseline**.

This is the single most useful thing measured so far, and it cuts against my own Phase 3
write-up. With 2 reps and a single-task suite, a coin-flip lint result has a 50% chance of
presenting as a clean conventions delta between arms. UNSTABLE exists precisely for this, and
Phase 5 must apply it to non-critical graders too, not only critical ones -- otherwise the
conventions row in the report inherits the noise while looking authoritative.

### The permission allowlist is too narrow in practice

Still one denial per trial. The agent does not issue `python -m pytest ...`; it issues

```
cd "<workspace>" && python -m pytest tests/acceptance/test_rounding.py -q && python -c "..."
```

`Bash(python -m pytest*)` cannot match a compound command that starts with `cd` and chains
with `&&`. So the agent still cannot verify its own work, and the Phase 3 finding stands
unresolved despite the fix.

Options for Phase 6: broaden to `Bash(cd *)` plus `Bash(python*)` (permissive but still not a
general shell), or accept the denial and state in DESIGN.md that verification was unavailable
to both arms. Leaning toward broadening -- the candidate AGENTS.md instruction is still
unfollowable otherwise, which is the whole reason this was changed.

### Cost: suggestive support for the ordering bias

Same task, same arm, minutes apart:

| run | cost | wall | cache read | cache create |
|---|---|---|---|---|
| smoke-01 | $0.2971 | 46.2s | 304,813 | 53,061 |
| smoke-02 | $0.1453 | 34.2s | 299,872 | 14,126 |

Cache creation fell 3.8x and cost fell 2.0x for identical work. **Confounded** -- the command
template changed between the two runs (`--allowedTools` was added), which alters the prompt
prefix. So this is consistent with the warm-cache hypothesis rather than proof of it. The
controlled test in Phase 6 (same arm twice back-to-back, nothing else changed) still needs to
happen, but a 2x swing on identical work is a strong argument for never reporting an absolute
per-task cost.

### Design notes

- `GraderStatus.VOID` added. A held-out overlay whose destination already existed cannot be
  read as a pass or a fail: the agent may have seen the tests, so a pass is meaningless and a
  fail accuses it of a defect nobody demonstrated. `Trial.measurable` is False when any
  critical grader is VOID, and such trials are excluded from outcomes in Phase 5 -- the same
  treatment infrastructure errors get.
- Overlay source is resolved by convention (`overlay: heldout` -> `task.heldout_tests`) rather
  than a branch per overlay kind, so a new overlay is a Task field plus a line of YAML.
- Two graders may share one overlay; the second does not trip the "already exists" assertion.
  Covered by a test, because the natural implementation gets this wrong.
- ERROR trials are not graded at all -- there may be no workspace, and a fabricated FAIL would
  be a false defect.
- Every test in `test_graders.py` matches the failure *reason*, not just the status. FAIL,
  TIMEOUT and VOID are three things the report must keep apart, and a test asserting only
  `status is FAIL` passes for all three.

State: `ruff` clean, `mypy` clean on 11 files, **27 tests green**.

---

## [T+4:00] Phase 5: comparator. Gate met.

68 tests green, `ruff` and `mypy` clean, and **100% branch coverage on comparator.py**:
every branch of the §4 rule has a case.

### The rule is data, not prose

`RULES` is an ordered list of `Rule(name, text, recommendation, predicate)`. `apply_rules`
walks it top-down and returns the rule object that fired; the report prints `rule_fired` and
renders `rule_text` from the same list. A template restating the policy in English could
drift from the code as the thresholds move. This cannot: there is one definition and both the
decision and its explanation come from it.

The ordering *is* the policy, and the first rule is the one that matters:
`regression_present` outranks everything, so three improvements alongside one regression is
still NEGATIVE. Tested explicitly, because that is the case where an aggregate score would
say the opposite.

### Where PLAN.md §4 was ambiguous

§4 words the FAIL arm as "all critical graders fail in ALL reps". Read literally, a rep where
two of three critical graders passed is neither PASS nor FAIL, and the task falls through to
UNSTABLE for no good reason. Implemented the operative unit as the **trial verdict**, did
every critical grader pass, so FAIL means every measured rep failed to clear that bar.
Deviation recorded in the docstring rather than silently chosen.

### Two exclusions in the cost summary, both load-bearing

1. **Successful trials only.** A candidate that gives up early is cheaper and worse.
2. **Paired by task.** Tasks where only one arm succeeded are dropped entirely. Without this,
   the two averages cover different task mixes and the delta measures *which tasks each arm
   happened to solve* rather than what either cost. §4 only asked for (1); (2) is the one
   that actually keeps the number honest.

Caveats live on `CostSummary` as data, including the prompt-cache mechanism, so the number
and the reason it needs qualifying travel together.

### Caught by running build_report on real data

Ran it against `runs/smoke-02`, which has one baseline trial and no candidate. Output:

```
correctness  base=1/1 cand=0/1
fidelity     base=1/1 cand=0/1
regression   base=1/1 cand=0/1
conventions  base=1/1 cand=0/1
```

**`cand=0/1` is a lie.** The candidate was never measured; it did not fail four dimensions.
Anyone reading that table would conclude the candidate arm was catastrophic. The unit tests
all passed, because every fixture happened to supply both arms.

Fixed by pairing the dimension rollup the same way cost is paired: a task counts only when
both arms produced a verdict for that dimension. The same run now reads `0/0` across the
board, which is the truth. Test added.

This is the second time a bug survived a green unit suite and was caught only by pointing the
tool at real output (the first was the venv PATH bug in Phase 4). Both were *silent*, a
plausible-looking wrong number, not a crash. Worth stating in DESIGN.md: the unit tests
protect the logic, but only running the thing on real artifacts catches the cases where the
logic is right and the presentation lies.

### Additions beyond §4, all from earlier decisions

- `Outcome.UNMEASURED` / `Transition.UNMEASURED`: no rep produced a trustworthy verdict.
  Distinct from FAIL: an absence of evidence, not evidence of a defect. Covers the
  infrastructure-error exclusion decided at T+2:40 and the VOID overlay from T+3:20.
- **Dimension rollups get UNSTABLE too**, not just critical outcomes, the fix required by
  the ruff I001 flapping in Phase 4. `DimensionSummary.noisy` is True when either arm
  disagreed with itself across reps, so the report can refuse to present a delta drawn from a
  self-inconsistent dimension.
- `divergences_for` flags any trial where acceptance passed and held-out failed, and
  `build_report` promotes it to a top-level caveat: "A green suite did not mean correct
  behaviour here." That is the assignment's central claim, stated only when measured.
- Confidence is never HIGH, asserted in a test (`not hasattr(Confidence, "HIGH")`) so a
  later well-meaning addition trips it.

---

## [T+4:40] Phase 6: four tasks built, FULL RUN LAUNCHED

**Run id `full-01`, 16 trials (4 tasks x 2 harnesses x 2 reps), launched in the background.**
Console log tees to `runs/full-01.console.log`.

Before launch, both repos green: evaluator 68 tests / ruff / mypy clean; unmodified demo repo
21 tests / ruff / mypy clean.

### The suite

| Task | Dimension | Acceptance suite | Held-out covers |
|---|---|---|---|
| `fix-rounding` | fidelity | deliberately weak, non-half values only | half-way values, negatives |
| `add-retry` | correctness | adequate, control task | wait contract, exception identity |
| `refactor-config` | regression | comments at line start only | trailing and indented comments |
| `add-cli-flag` | conventions | flag parses | range validation, `docs/cli.md` updated |

Repo conventions are now machine-checked: ruff `select = ["E","F","I","D","ANN"]` and mypy
`strict = true`, so "docstrings and complete type annotations" is enforced by the existing
lint and types graders rather than needing a bespoke grader.

### Two bugs the probe trials caught, both worth the $0.22

Ran two single-trial probes before committing to the full run. Both found real defects.

**1. `AGENTS.md` was being counted as the agent's work.** `create_workspace` did
`git init && commit`, and the adapter copied the instructions in *afterwards*. So AGENTS.md
was untracked and appeared in `files_changed` and `patch.diff`, **for the candidate arm
only**. Every candidate patch would have looked larger than every baseline patch, for a file
the agent never touched.

Fixed by applying harness instructions *before* the initial commit. The harness config is the
environment under test, not the work; it belongs to the workspace baseline. `prepare()` is now
an assertion that the copy happened, not the copy itself.

**2. `__pycache__/` leaked into the patch.** A direct consequence of the permission fix: the
agent can now run pytest, which writes caches into the workspace. `files_changed` showed
`src/demo/__pycache__/` and `tests/acceptance/__pycache__/`. Fixed with a `.gitignore` in the
demo repo, which a real Python repo would have anyway.

After both fixes the same probe reports `files_changed: ['src/demo/retry.py']`. Clean.

**3. The broadened allowlist works.** `"Bash(cd *)" "Bash(python *)" "Bash(ruff *)"
"Bash(mypy *)"` gives **0 permission denials**, down from 1 on every prior trial. The agent
can finally run the checks the candidate AGENTS.md asks it to run, so that instruction is now
capable of having an effect.

### Disclosure: the line in AGENTS.md most at risk of being a strawman

The candidate AGENTS.md ends with:

> Tickets state the required behaviour in full. The tests that ship with a ticket cover the
> common path and are usually not exhaustive, implement what the ticket says, not only what
> the tests check.

This is a realistic instruction and a common one in real AGENTS.md files. It is also, by some
distance, **the line most likely to move the held-out metric**, which is exactly what this
experiment measures. I am keeping it and flagging it rather than quietly removing it: if the
candidate wins on fidelity, that sentence is the most probable cause, and the write-up has to
say so instead of implying the whole file did the work.

Nothing else in the file is task-specific. The conventions it states are all independently
discoverable from `pyproject.toml` and `docs/cli.md`, AGENTS.md makes them salient; it does
not make them secret. That is the honest version of this comparison: the baseline *could*
find them, and the question is whether it does.

### Early signal from the probes (single trials, not evidence)

`probe-02`, candidate on `add-retry`: acceptance pass, held-out pass, regressions pass, lint
pass, **types FAIL**. Worth watching whether mypy strict is where the arms actually separate.

---

## [T+5:00] full-01 complete: 16/16 trials, 832s, $2.86, no errors or timeouts

```
RECOMMENDATION : INCONCLUSIVE   (rule: no_clear_signal)
CONFIDENCE     : LOW
```

| task | baseline | candidate | transition |
|---|---|---|---|
| fix-rounding | PASS | PASS | PASS->PASS |
| add-retry | PASS | PASS | PASS->PASS |
| refactor-config | PASS | PASS | PASS->PASS |
| add-cli-flag | FAIL | FAIL | FAIL->FAIL |

| dimension | baseline | candidate | noisy |
|---|---|---|---|
| correctness | 4/4 | 4/4 | no |
| fidelity | 3/4 | 3/4 | no |
| regression | 4/4 | 4/4 | no |
| **conventions** | **3/4** | **0/4** | **yes (2 unstable)** |

Cost: baseline $0.1776, candidate $0.1507, **-15.1%**. Wall: -10.0%.

### Finding 1: the candidate is WORSE on conventions, which is the opposite of the hypothesis

The candidate AGENTS.md exists largely to state conventions, and the candidate scored 0/4
against the baseline's 3/4. Per-trial grader matrix:

| task | arm | lint | types |
|---|---|---|---|
| fix-rounding | baseline | pass pass | pass pass |
| fix-rounding | candidate | pass **fail** | pass pass |
| add-retry | both arms | pass pass | **fail fail** |
| refactor-config | baseline | pass pass | pass pass |
| refactor-config | candidate | pass pass | **fail fail** |
| add-cli-flag | baseline | pass pass | pass pass |
| add-cli-flag | candidate | **fail** pass | pass pass |

The one **consistent** effect is refactor-config: the candidate fails `mypy --strict` in both
reps, the baseline passes in both. The error is the same class each time, at slightly
different lines:

```
src/demo/config.py:57: error: Call to untyped function (unknown) in typed context
src/demo/config.py:64: error: Call to untyped function (unknown) in typed context
```

The candidate extracted an unannotated helper and called it from annotated code. A plausible
causal story: the candidate does more *structural* work, which creates more new functions,
which creates more surface for a convention violation, and the AGENTS.md instruction to
annotate everything did not prevent it. That is a hypothesis from n=2, not a conclusion, but
it is the kind of trade-off a single score would have hidden entirely.

The other two conventions failures are single-rep flips (UNSTABLE), consistent with the lint
flapping already seen in Phase 4. The comparator correctly refused to count them.

### Finding 2: `add-retry` fails `types` in all four trials. That is my task's bug, not a result

```
src/demo/retry.py:16: error: Missing return statement  [return]
```

A retry loop whose final action is `raise` inside the loop cannot be proven to return by
mypy; the natural implementation of my own ticket trips strict mode. **Both arms fail
identically**, so it contributes nothing to the delta, but it drags both arms' conventions
score down and makes the dimension look worse than the harnesses deserve.

A grader that fails identically in every arm is measuring the task, not the evaluand. The
report should surface "this grader never varied" rather than quietly folding it into a
dimension. Fix candidate for Phase 7: flag dimensions where no trial in either arm passed.

### Finding 3: both arms ignored an explicit written instruction

`add-cli-flag` is FAIL->FAIL, and the held-out breakdown is precise: **3 of 4 held-out tests
passed in every trial**. Both arms implemented the 0-6 range validation and the non-integer
rejection correctly. The only failure, in all four trials, is:

```
FAILED tests/heldout/test_cli_heldout.py::test_the_new_flag_is_documented
```

Neither arm updated `docs/cli.md`. The candidate AGENTS.md says, verbatim:

> Any flag the `demo` command accepts must appear in the table in `docs/cli.md`.

It was told, in the file under test, and did not do it, in both reps. `files_changed` is
`['src/demo/cli.py']` for all four trials, so this is not a grading artefact.

This is the most useful null result in the run: **writing an instruction into AGENTS.md is
not the same as the instruction being followed.** A team that shipped this AGENTS.md on the
strength of having written it down would be wrong, and only a held-out check would tell them.

### Finding 4: my Phase 5 fix for the cost ordering bias was wrong

Alternating arm order per rep produces the sequence `b0, c0, c1, b1`. Baseline therefore
occupies execution positions **1 and 4**, and the candidate occupies **2 and 3**, both warm.
The alternation did not counterbalance anything.

Measured on this run:

```
                    pos1      pos2      pos3      pos4
MEAN              $0.2005   $0.1763   $0.1620   $0.1752

position 1 (cold cache) vs positions 2-4:  first trial of a task costs +17.2%
baseline (positions 1,4)  mean $0.1879
candidate (positions 2,3) mean $0.1691   ->  -10.0% from POSITION ALONE
```

The report's headline cost figure is **-15.1%**. Roughly two thirds of it is an artefact of
where each arm sits in the execution order.

I introduced this bias, then "fixed" it, then shipped a fix that left most of it in place,
and none of the 68 unit tests could have caught it, because it is a property of the
*schedule*, not of any function. It surfaced only from reading per-trial costs in execution
order.

Correct fix for the next run: counterbalance across tasks as well as reps, so each arm takes
position 1 an equal number of times. Until then the cost dimension must be reported with this
measured artefact stated next to the number, not as a clean -15%.

---

## [T+5:10] Counterbalancing fixed, full-02 launched

Schedule is now counterbalanced on `(task_index + rep) % 2`, not on `rep` alone. Verified
before spending anything on it:

```
fix-rounding      baseline -> candidate -> candidate -> baseline
add-retry         candidate -> baseline -> baseline -> candidate
refactor-config   baseline -> candidate -> candidate -> baseline
add-cli-flag      candidate -> baseline -> baseline -> candidate

position-1 (cold cache) count: {'baseline': 2, 'candidate': 2}
```

`full-02` launched at 13:27:49Z. **The task suite is frozen**: `full-02` differs from
`full-01` only in trial ordering, so the cost artefact becomes measurable by comparing the
two rather than merely asserted. Deliberately did *not* fix the `add-retry` mypy defect at
the same time, changing the instrument and the schedule in one step would make the runs
incomparable and would look like tuning until the answer came out right.

---

## [T+5:40] Phase 7: report layer. Gate met.

83 tests green, `ruff` and `mypy` clean.

**142 markdown links and 112 JSON evidence paths checked automatically: 0 broken.** Then
three followed by hand, because existence is not the same as supporting the claim:

| Claim in report.md | Followed to | Holds? |
|---|---|---|
| conventions: candidate 0/4, Δ -3 | `refactor-config/candidate/0/graders/types.log` -> real mypy error; baseline log -> `Success` | yes |
| "a green suite did not mean correct behaviour" | `add-cli-flag/candidate/0/graders/heldout.log` -> `1 failed, 3 passed`, named test; acceptance log on the same trial -> `2 passed` | yes |
| candidate cost $0.1507/trial | `fix-rounding/candidate/0/transcript.json` -> `total_cost_usd: 0.1434` in the agent's own envelope | yes |

### Decisions in this phase

- **The rule is printed from `comparator.RULES`, not restated in the template.** A test
  asserts every rule name appears in the rendered body, so adding a rule without surfacing it
  fails the suite.
- **`report.json` carries `rule.inputs`**: the actual counts the predicates were evaluated
  against, so a consumer can recompute the verdict rather than trusting it.
- **The business-fidelity checklist is generated empty and a test asserts no box is
  pre-ticked.** It is the one part of the report the tool refuses to answer.

### Three bugs found while rendering

1. **Every link on every task page was broken.** Task pages live in `tasks/`, one level below
   `trials/`, so `trials/...` resolved to `tasks/trials/...`. They rendered perfectly and all
   404'd. This is the failure mode the phase brief names: a number that *looks* auditable and
   is not. Caught by a link-resolution check, now a test.
2. **A caveat claimed a mitigation the run did not have.** The cost caveat said "arm order is
   alternated per rep to cancel the advantage", and `full-01` is exactly the run where that
   alternation failed to cancel anything. Fixed by recording `schedule` in the manifest and
   having the report state what *this* run did: runs without counterbalancing now carry an
   explicit warning that the cost delta is an upper bound, not a measurement.
3. **"Graders that never varied" overclaimed.** I first wrote it as "treat it as an instrument
   defect". But the section caught two rows, and only one is a defect:
   - `add-retry`/`types`: genuine instrument defect, no correct solution satisfies it
   - `add-cli-flag`/`heldout`: a genuine shared failure, both arms really did skip the docs

   They are indistinguishable to the tool. The section now says so and tells the reader to
   open the log to decide which they have, rather than labelling both a defect.

### Note for Phase 8

`full-01` shows permission denials on several trials despite the probe showing zero. The
allowlist is not covering everything the agent reaches for. Worth reading the denial payloads
during hand inspection.

---

## [T+6:00] full-02 replication: the run that broke my own conclusions

16/16 trials, 881s, $2.70. Same suite, same config, **only the trial ordering differs**.

| | full-01 | full-02 |
|---|---|---|
| recommendation | INCONCLUSIVE / LOW | INCONCLUSIVE / LOW |
| transitions | identical: 3 PASS->PASS, 1 FAIL->FAIL | identical |
| correctness | 4/4 -> 4/4 | 4/4 -> 4/4 |
| fidelity | 3/4 -> 3/4 | 3/4 -> 3/4 |
| regression | 4/4 -> 4/4 | 4/4 -> 4/4 |
| **conventions** | **3/4 -> 0/4** | **2/4 -> 3/4** |
| **cost delta** | **-15.1%** | **-3.0%** |
| wall delta | -10.0% | +11.0% |

### The conventions dimension reversed sign

In full-01 I wrote up `refactor-config` as *"the one **consistent** effect: the candidate
fails mypy strict in both reps, the baseline passes in both."* Per-trial, full-02:

```
refactor-config  baseline   rep0: types=FAIL  rep1: types=pass     <- baseline now flaps
refactor-config  candidate  rep0: types=pass  rep1: types=pass     <- candidate now clean
```

**The effect did not merely weaken. It inverted.** A 2-of-2 versus 0-of-2 split looked like
strong evidence inside one run, and replication showed it was a coin flip. The same is true
of both lint failures: `fix-rounding`/candidate and `add-cli-flag`/candidate each failed lint
once in full-01 and passed cleanly in full-02.

Had I shipped full-01 alone, the report would have said the candidate is markedly worse on
conventions. Had I shipped full-02 alone, it would have said the candidate is better. Neither
is true. **Nearly every conventions signal in this suite is unreplicated**, and the exception
is the
`add-retry`/`types` instrument defect, which failed 4/4 in both arms in both runs, the only
reproducible thing in the entire dimension.

The tool did flag conventions as `noisy` in both runs, which is right but not sufficient:
in full-01 the candidate was FAIL/FAIL on refactor-config, perfectly consistent *within* that
run. **Within-run UNSTABLE detection cannot see between-run instability.** At 2 reps, a
dimension result that looks consistent is not yet evidence. That is a limitation of the
design, not a bug, and it belongs in DESIGN.md rather than being quietly fixed.

### My cost diagnosis was also wrong

The counterbalancing worked in the sense that the delta collapsed:

```
full-01 (baseline in the cold slot 4/4 times): cost delta -15.1%
full-02 (cold slot split 2/2):                 cost delta  -3.0%
```

So roughly 80% of the "candidate is 15% cheaper" headline was an artefact of scheduling. That
part holds.

But the *mechanism* I asserted does not:

```
full-01: first-trial-in-task premium  +17.2%
full-02: first-trial-in-task premium  -11.0%
```

The cold-slot premium reversed sign too. So the cache-creation story I wrote up at T+5:00 with
confidence is not supported. The defensible conclusion is narrower and less satisfying:
**per-trial cost is dominated by run-to-run variance at this scale, and the -15.1% was noise
that happened to align with arm position.** Counterbalancing remains correct practice, it
stops variance from aligning systematically with one arm, but it is not what "fixed" the
number. Replication is what revealed the number was never real.

Two corrections to my own earlier write-ups, then. I diagnosed a mechanism, shipped a fix for
it, and the replication showed the diagnosis was wrong as well as the original number.

### What actually replicated across both runs

Only three things, and they are the only claims the report should make with any confidence:

1. **Every task's transition is identical in both runs.** 3 PASS->PASS, 1 FAIL->FAIL. The
   critical-grader outcomes are stable; the non-critical dimensions are not.
2. **`add-cli-flag` fails held-out in all 8 trials across both runs**, always on the same
   test: neither arm updated `docs/cli.md`, despite the candidate AGENTS.md instructing it in
   writing. This is the strongest finding in the project and it is a null result about
   AGENTS.md efficacy.
3. **`add-retry`/`types` fails 4/4 in both arms in both runs.** Instrument defect, confirmed
   by replication.

### Implication for the deliverable

The honest headline stands: **INCONCLUSIVE, LOW confidence, this AGENTS.md revision shows no
measurable effect on engineering outcomes at this scale.** Two independent 16-trial runs agree
on that, and disagree on everything finer-grained. A tool that had reported the full-01
conventions delta as a finding would have been confidently wrong, and the only reason I know
that is that I ran it twice.

---

## [T+6:40] Phase 8: hand inspection. Four reads, four answers.

Read the artifacts, not the summaries. For each: what the tool reported, what the code
actually does, and whether the tool or the task was wrong.

### 1. `fix-rounding`, all eight patches: the tool was right, the task was fair

**Tool reported:** PASS -> PASS in both runs, held-out passing in all 8 trials.

**The code:** all eight patches are functionally the same implementation:
`float(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))`. One trial
used `scaleb`/`to_integral_value`, which is equivalent. Every one honours the half-away-from-
zero rule and the negative-credit rule the ticket states.

**Verdict: the tool was right.** Nothing passed acceptance and failed held-out here. The trap
I built in Phase 1 never fired, in 8 attempts across two runs.

That is worth stating plainly rather than burying: **the deliberately weak acceptance suite
did not catch anybody out.** The held-out tests earned their place by *proving the trap did
not fire*, not by catching a defect. A fair ticket plus a capable model is enough; the
fidelity dimension paid for itself elsewhere (see §3 below), not here.

### 2. The conventions reversal: the tool was right, my reading of it was wrong

**Tool reported:** full-01 conventions 3/4 -> 0/4, driven by `refactor-config` where the
candidate failed `mypy --strict` in *both* reps and the baseline passed in both. I wrote that
up as "the one consistent effect". full-02 reported 2/4 -> 3/4 on the same suite.

**The code.** Both failing trials hit the identical error, `Call to untyped function
(unknown) in typed context [no-untyped-call]`, and the cause is one line:

```python
coerce = _COERCERS.get(key, lambda v: v)   # <- unannotated lambda, mypy strict rejects it
settings[key] = coerce(value)              # <- the line mypy flags
```

Correlation across all eight `refactor-config` trials is perfect:

| run | arm | rep | `lambda` in config.py | types |
|---|---|---|---|---|
| full-01 | baseline | 0, 1 | 0 | pass, pass |
| full-01 | candidate | 0, 1 | 1, 1 | **fail, fail** |
| full-02 | baseline | 0 | 1 | **fail** |
| full-02 | baseline | 1 | 0 | pass |
| full-02 | candidate | 0, 1 | 0 | pass, pass |

8/8: lambda present -> FAIL, absent -> PASS.

**Verdict: the tool was right about every individual trial. I was wrong about what they
meant.** mypy genuinely errored each time. What I read as a harness effect is a coin flip
over *implementation shape*, does the model reach for a bare `lambda v: v` as the dispatch
default, or annotate it? Three of eight trials did; which arm they landed in is chance.

This is the finding I did not trust, and the reason I did not trust it is that I ran the
whole thing a second time. Nothing inside full-01 could have told me. The candidate was
FAIL/FAIL (perfectly self-consistent) so the `noisy` flag did not fire on the deciding
task. **Within-run UNSTABLE detection cannot see between-run instability, and a 2-of-2
versus 0-of-2 split is not evidence at 2 reps.**

**Fixed:** the report now carries an explicit caveat that dimension deltas at reps <= 2 are
unreplicated, naming this inversion as the reason. It does not suppress the number, it
refuses to let the number be read as a finding.

### 3. Cheapest vs most expensive trial: the gap is real work, but partly my fault

**Tool reported:** cheapest $0.0947, most expensive $0.2947, a 3.1x spread.

**The trials:** cheapest is `add-retry`/candidate, 4 turns, 20.9s, 701B patch, all critical
graders PASS. Most expensive is `add-cli-flag`/candidate/1, 21 turns, 88.8s, 1113B patch.
Neither crashed; no timeouts anywhere in 32 trials. So the spread is genuine work.

**But the expensive one carries 6 permission denials**, all of this shape:

```
cd "<workspace>" && PYTHONPATH=src python -m pytest ...
```

An env-var prefix does not match `Bash(python *)`. Across both runs: **14 denials in 32
trials, and they are asymmetric**, `add-cli-flag`/candidate took 10 against baseline's 2.

**Verdict: the evaluator was wrong.** And the asymmetry has a mechanism: the candidate
AGENTS.md instructs the agent to run the checks, so it attempts more commands, so more of its
attempts hit the gap in my allowlist, so it burns turns retrying. **My permission
configuration differentially penalised the arm whose instructions tell it to do more work**,
and cost and turn count are exactly what that inflates.

**Fixed, two ways.** The allowlist now covers `PYTHONPATH=*` and bare `*python -m pytest*`
forms, which applies to future runs only and does not disturb full-01/full-02. And the report
now reports denial counts per arm, escalating to an explicit warning when one arm is blocked
disproportionately. full-02 now says: *"The evaluator blocked the candidate arm 8 times
against 1 for baseline. Blocked attempts cost turns, so part of this cost difference is the
permission configuration, not the harness."*

### 4. `add-retry`, a PASS -> PASS task: "unchanged success" hides nothing here

**Tool reported:** PASS -> PASS, identical in both runs.

**The code:** both arms wrote the same retry loop, differing only in whether the counter runs
`range(attempts)` or `range(1, attempts + 1)`. Same semantics, same structure, same docstring
content. No quality difference a reviewer would care about, and none the graders are missing.

**Verdict: the tool was right, and so was the "unchanged" label.** Both arms also fail
`mypy --strict` with `Missing return statement`, because a `for` loop whose last action is
`raise` cannot be proven to return, confirming the instrument defect in my own ticket rather
than anything about either harness. The report already isolates this under "graders that never
varied between the arms".

### What I changed as a result

- report: dimension deltas at reps <= 2 are labelled unreplicated, citing the observed
  inversion
- report: per-arm permission-denial counts, with a warning when they are lopsided enough to
  confound cost
- config: allowlist widened to cover env-var-prefixed commands (future runs only)

### What I deliberately did not change

- **The task suite stays frozen.** The `add-retry` mypy defect is real and I could fix the
  ticket, but doing so after seeing the results would make full-01 and full-02 incomparable
  and would look like tuning until the answer came out right. It is reported as an instrument
  defect instead.
- **No re-run.** Every fix above is in the report layer or in config for future runs. Both
  reports were re-rendered from existing artifacts in under a second, which is the entire
  reason `run` and `report` are separate commands.

# Process

How this was built, what I checked by hand, and where the agent was wrong.

## Agent setup

- **Agent:** Claude Code 2.1.272 / 2.1.273 (VSCode extension), Opus, effort `xhigh`.
- **[`AGENTS.md`](AGENTS.md)** : the instructions governing work on the evaluator itself.
  Not to be confused with `examples/harnesses/*/AGENTS.md`, which are the files *under test*
  in the experiments.
- **[`PLAN.md`](PLAN.md)** : the phase plan written before any code, with per-phase gates
  and a degradation ladder. Written after analysing the brief against the requirement doc and
  finding ten gaps in it, including a missing deliverable.

## Prompts

[`prompts/`](prompts/) holds the phase prompts, indexed in
[`prompts/00-README.md`](prompts/00-README.md). They were written up front as a plan and
pasted one per session.

The sequence recorded there is what happened, not what was planned: **phase 2 was never
pasted.** Its modules (`models.py`, `config.py`, `cli.py`) were built inside phase 3, because
`harness-eval run` cannot be wired without them. I flagged that at the time rather than
silently absorbing it, and a later audit found phase 2 was only ~60% done, missing
`TaskComparison`, `EvaluationReport`, dimension validation, and `tests/test_config.py`
entirely. Those were closed before phase 4.

## Transcript

[`transcripts/session-01-raw.jsonl`](transcripts/session-01-raw.jsonl): the complete
session, 7.2 MB, untrimmed.
[`transcripts/session-01-readable.md`](transcripts/session-01-readable.md): the same 1,228
messages rendered, including every tool call and result.

## Where the agent was wrong

These are the entries from [`NOTES.md`](NOTES.md) where I got something wrong and the
evidence corrected me. Each one is a bug that a green test suite did not catch.

### 1. Every lint and types grader would have silently reported FAIL: in both arms

A grader test failed and I assumed the held-out overlay was polluting `ruff check .`. It was
not. Grader subprocesses inherited `os.environ` but **not the evaluator's venv**, so:

```
ruff check .   exit=1  'ruff' is not recognized as an internal or external command
mypy src       exit=1  'mypy' is not recognized as an internal or external command
pytest -q      exit=2  (resolved to the SYSTEM python's pytest, not the venv's)
```

`ruff` and `mypy` did not resolve at all. They exit 1 with empty stdout, which the grader
maps to `FAIL`, identically to a real lint failure. Both are non-critical, so nothing would
have blocked; the report would simply have stated "lint-clean 0/4 -> 0/4" with total
confidence. **A symmetric wrong number is the worst kind: the delta looks right and the
absolute is nonsense.** Fixed by putting the evaluator's interpreter directory first on
`PATH`. See NOTES.md `[T+3:20]`.

### 2. The report rendered "candidate 0/1" for an arm that was never measured

Running `build_report` against a baseline-only run produced:

```
correctness  base=1/1 cand=0/1
fidelity     base=1/1 cand=0/1
```

`cand=0/1` is a lie. The candidate did not fail four dimensions, it was never run. Anyone
reading that table would conclude the candidate arm was catastrophic. **Every unit test
passed**, because every fixture happened to supply both arms. Fixed by pairing the dimension
rollup the way cost is paired: a task counts only when both arms produced a verdict. See
NOTES.md `[T+4:00]`.

### 3. I diagnosed a cost bias, shipped a fix, and the fix was also wrong

`full-01` reported the candidate 15.1% cheaper. I traced it to prompt-cache mechanics (the
arm running first pays to build the cache) and fixed the schedule to alternate arm order per
rep. That produces `b, c, c, b` for every task, which leaves the **baseline in execution
position 1 every single time**. Measured: position 1 costs +17.2% over positions 2-4, handing
the candidate ~10% from scheduling alone. The "fix" removed almost none of the bias.

Properly counterbalanced on `(task + rep)`, the delta fell from **-15.1% to -3.0%**. And the
replication undermined my mechanism too: the cold-slot premium was +17.2% in one run and
-11.0% in the other. The honest conclusion is narrower than the one I first wrote: per-trial
cost is dominated by run-to-run variance at this scale. See NOTES.md `[T+5:00]` and
`[T+6:00]`.

### 4. `AGENTS.md` was being counted as the agent's own work

Probe trials before the first full run showed `files_changed: ['AGENTS.md', ...]`. For the
candidate arm only. `create_workspace` committed, *then* the adapter copied the instructions
in, so the harness's own config file appeared in the candidate's patch and never in the
baseline's. Every candidate diff would have looked larger for a file the agent never touched.
Fixed by applying instructions before the initial commit. Two probe trials, $0.22, two real
bugs. See NOTES.md `[T+4:40]`.

### 5. Every link on every task page was broken

Task pages live in `tasks/`, one level below `trials/`, so `trials/...` resolved to
`tasks/trials/...`. They rendered perfectly and 404'd on click, precisely the failure the
assignment warns about: a number that *looks* auditable and is not. Now a test. See NOTES.md
`[T+5:40]`.

### 6. A caveat claimed a mitigation the run did not have

The cost caveat read "arm order is alternated per rep to cancel the advantage", and `full-01`
is exactly the run where that alternation cancelled nothing. Fixed by recording the schedule
in the manifest and having each report state what *that* run actually did.

## What I checked by hand

Phase 8 was a full pass of reading artifacts rather than summaries: eight `fix-rounding`
patches, both arms of the conventions reversal, the cheapest and most expensive trials, and a
`PASS->PASS` task to see whether "unchanged" was hiding anything. That pass produced
[`DESIGN.md`](DESIGN.md) §4 and two report-layer changes. NOTES.md `[T+6:40]`.

Before every task shipped, I verified the trap fired: wrote a naive implementation by hand,
confirmed it passed the visible suite and failed held-out, then reverted. A held-out suite
that cannot fail is decoration.

## Honest limits

- The local-model experiments (`html-01`, `cleaner-01`) use a fixed three-step runner I
  wrote, not an agentic loop. They measure the model's text output, not its behaviour as an
  agent.
- Six experiments and 104 trials produced no case where an `AGENTS.md` moved a grader. The
  instrumentation shows why (the agent reads the file and does not follow its most specific
  instruction) but "advisory guidance does not help" is a conclusion about *these* tasks and
  *this* model, not a general one.

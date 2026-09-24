Evaluation Report

Harness Change:
Harness 1 is told in AGENTS.md to run pytest, ruff and mypy --strict before finishing. Harness 2 is told nothing and instead carries a .claude/ Stop hook that runs the same three checks and blocks completion while any of them fails. Same model, same task, same tools, permissions, budget and environment. Prose against mechanism.

Baseline:
Harness 1 - Haiku + AGENTS.md asking for the checks (prose)

Candidate:
Harness 2 - Haiku + a Stop hook that runs the checks (mechanism)

Models:
Baseline  claude-haiku-4-5  via default (CLI-configured)
Candidate claude-haiku-4-5  via default (CLI-configured)

Controlled:
YES. Intended variable: instructions, config_dir

Run:
hook-01: 1 tasks x 2 harnesses x 8 reps = 16 trials

================================


Task Outcomes

notify-fallback:
UNSTABLE -> UNSTABLE  (UNSTABLE - excluded from counts)

Improved:
0

Regressed:
0

Excluded from those counts:
1 unstable, 0 unmeasured

Evidence:

Per-task detail:
tasks/notify-fallback.md

================================


Correctness

Baseline:
1/1

Candidate:
1/1

Evidence:

acceptance:
Baseline passed 8/8 trials
Candidate passed 8/8 trials

================================


Fidelity

Baseline:
0/1

Candidate:
0/1

NOT SELF-CONSISTENT:
1 baseline and 1 candidate task(s) gave
different results across reps of the same harness. Any difference above is at least
partly noise.

Evidence:

heldout:
Baseline passed 3/8 trials
Candidate passed 6/8 trials
Example failure log: trials/notify-fallback/baseline/0/graders/heldout.log

================================


Regression

Baseline:
1/1

Candidate:
1/1

Evidence:

regressions:
Baseline passed 8/8 trials
Candidate passed 8/8 trials

================================


Conventions

Baseline:
0/1

Candidate:
1/1

NOT SELF-CONSISTENT:
1 baseline and 0 candidate task(s) gave
different results across reps of the same harness. Any difference above is at least
partly noise.

Evidence:

lint:
Baseline passed 7/8 trials
Candidate passed 8/8 trials
Example failure log: trials/notify-fallback/baseline/2/graders/lint.log

types:
Baseline passed 8/8 trials
Candidate passed 8/8 trials

================================


Cost

Baseline:
$0.0928 per successful trial
320k tokens per trial

Candidate:
$0.1161 per successful trial
526k tokens per trial

Change:
+25.1% cost, +64.2% tokens, +15.9% wall-clock

NEGATIVE IMPACT

Total spent across all trials, successful or not:
Baseline  $0.7219 over 8 trial(s)
Candidate $0.9283 over 8 trial(s)

Evidence:

Trials counted:
9 counted, 0 excluded

Per-trial figures:
each trial's own transcript.json, field total_cost_usd

Caveat:
Successful trials only. Failed and unmeasured trials are excluded, so a cheap failure cannot look like an efficiency gain.

Caveat:
Paired by task: tasks where only one arm succeeded are dropped, so the two averages cover the same work.

Caveat:
Cost is dominated by prompt-cache mechanics, and cache creation is priced far above cache read, so whichever arm runs first in a task pays more. Small deltas should not be read as harness effects.

Caveat:
Arm order was counterbalanced across tasks and reps, so each arm took the cold-cache first slot equally often.

Caveat:
The evaluator blocked the baseline arm 2 time(s) against 0 for candidate. Blocked attempts cost turns, so part of this cost difference is the permission configuration, not the harness.

================================


Business Fidelity

Not generated. The graders answer "do the tests pass". They cannot answer "is this what
the business asked for". Fill this in after reading the patches.

[ ] notify-fallback:
Read both arms' patches at tasks/notify-fallback.md. Does the candidate's change do
what the ticket asked, beyond satisfying the tests?

[ ] Any patch you would reject at code review?

[ ] Any patch that edited tests rather than source?


================================


Final Recommendation:

NEGATIVE - LOW confidence

No task changed state in either direction. The suite could not distinguish the two
harnesses on the outcomes it measures.
Cost moved +25.1%: negative impact.

Human review recommended.


Why this verdict:

Rule fired:
costlier_for_nothing

The rule, evaluated top to bottom, first match wins. Printed from the same ordered list
the code evaluates, so it cannot drift from the decision:
1. regression_present: any task went PASS -> FAIL -> NEGATIVE
2. fewer_passes: the candidate passes fewer tasks than the baseline -> NEGATIVE
3. costlier_for_nothing: no task improved and cost rose more than 25% -> NEGATIVE
4. improved_without_regressing: at least one task improved and none regressed -> POSITIVE SIGNAL
5. no_clear_signal: no task changed state either way -> INCONCLUSIVE

Confidence is never reported as HIGH. A 1-task suite cannot
support a strong claim in either direction.

Read before acting:

- Confidence is LOW: 1 task(s) gave different outcomes across reps

- Confidence is LOW: no task changed state, so the comparison rests on unchanged results

- At least one trial passed its visible tests and failed the held-out tests. A green suite did not mean correct behaviour here.


================================


How To Verify Any Number Above

hook-01/
  report.md report.json         this report, and the same content as data
  tasks/<task>.md               per-task drill-down, both arms, every rep
  trials/<task>/<arm>/<rep>/
    patch.diff                  exactly what the agent changed
    transcript.json             the agent's own envelope: cost, tokens, turns
    prompt.txt command.txt      what it was asked, and how it was invoked
    graders/<id>.log            each grader's command, exit code and output

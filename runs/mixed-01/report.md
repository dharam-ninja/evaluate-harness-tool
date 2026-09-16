Evaluation Report

Harness Change:
Harness 1 is a 360M local model with no AGENTS.md, driven by a fixed single-shot runner. Harness 2 is Claude Sonnet with an AGENTS.md, driven by Claude Code's full agentic loop. Model, provider, runner and guidance all differ.

Baseline:
Harness 1 - smollm2:360m (local, Ollama), NO AGENTS.md, single-shot runner

Candidate:
Harness 2 - claude-sonnet-5 (Anthropic), WITH AGENTS.md, Claude Code agentic loop

Models:
Baseline  smollm2:360m  via http://localhost:11434/v1
Candidate claude-sonnet-5  via default (CLI-configured)

Controlled:
NO - see fairness in manifest.json. Intended variable: model, endpoint, command, instructions

Run:
mixed-01: 1 tasks x 2 harnesses x 4 reps = 8 trials

================================


Task Outcomes

html-contact:
FAIL -> PASS  (IMPROVED)

Improved:
1

Regressed:
0

Evidence:

Per-task detail:
tasks/html-contact.md

================================


Correctness

Baseline:
0/1

Candidate:
1/1

Evidence:

acceptance:
Baseline passed 0/4 trials
Candidate passed 4/4 trials
Example failure log: trials/html-contact/baseline/0/graders/acceptance.log

================================


Fidelity

Baseline:
0/1

Candidate:
1/1

Evidence:

heldout:
Baseline passed 0/4 trials
Candidate passed 4/4 trials
Example failure log: trials/html-contact/baseline/0/graders/heldout.log

================================


Regression

Baseline:
1/1

Candidate:
1/1

Evidence:

regressions:
Baseline passed 4/4 trials
Candidate passed 4/4 trials

================================


Conventions

Baseline:
1/1

Candidate:
1/1

Evidence:

validator:
Baseline passed 4/4 trials
Candidate passed 4/4 trials

================================


Cost

Baseline:
n/a per trial

Candidate:
n/a per trial

Change:
n/a cost, n/a tokens, n/a wall-clock

NOT MEASURED

Evidence:

Trials counted:
0 counted, 4 excluded

Per-trial figures:
each trial's own transcript.json, field total_cost_usd

Caveat:
Successful trials only. Failed and unmeasured trials are excluded, so a cheap failure cannot look like an efficiency gain.

Caveat:
Paired by task: tasks where only one arm succeeded are dropped, so the two averages cover the same work.

Caveat:
Cost is dominated by prompt-cache mechanics, and cache creation is priced far above cache read, so whichever arm runs first in a task pays more. Small deltas should not be read as harness effects.

Caveat:
4 successful trial(s) excluded by task pairing.

Caveat:
Arm order was counterbalanced across tasks and reps, so each arm took the cold-cache first slot equally often.

================================


Business Fidelity

Not generated. The graders answer "do the tests pass". They cannot answer "is this what
the business asked for". Fill this in after reading the patches.

[ ] html-contact:
Read both arms' patches at tasks/html-contact.md. Does the candidate's change do
what the ticket asked, beyond satisfying the tests?

[ ] Any patch you would reject at code review?

[ ] Any patch that edited tests rather than source?


================================


Final Recommendation:

POSITIVE SIGNAL - MODERATE confidence

Candidate improved 1 task(s) and regressed none.

Human review recommended.


Why this verdict:

Rule fired:
improved_without_regressing

The rule, evaluated top to bottom, first match wins. Printed from the same ordered list
the code evaluates, so it cannot drift from the decision:
1. regression_present: any task went PASS -> FAIL -> NEGATIVE
2. fewer_passes: the candidate passes fewer tasks than the baseline -> NEGATIVE
3. costlier_for_nothing: no task improved and cost rose more than 25% -> NEGATIVE
4. improved_without_regressing: at least one task improved and none regressed -> POSITIVE SIGNAL
5. no_clear_signal: no task changed state either way -> INCONCLUSIVE

Confidence is never reported as HIGH. A 1-task suite cannot
support a strong claim in either direction.


================================


How To Verify Any Number Above

mixed-01/
  report.md report.json         this report, and the same content as data
  tasks/<task>.md               per-task drill-down, both arms, every rep
  trials/<task>/<arm>/<rep>/
    patch.diff                  exactly what the agent changed
    transcript.json             the agent's own envelope: cost, tokens, turns
    prompt.txt command.txt      what it was asked, and how it was invoked
    graders/<id>.log            each grader's command, exit code and output

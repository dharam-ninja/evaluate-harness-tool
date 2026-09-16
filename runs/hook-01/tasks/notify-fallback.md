# `notify-fallback`

[← back to the report](../report.md)

**Baseline unstable -> Candidate unstable (UNSTABLE - excluded from counts)**

## A green suite did not mean correct behaviour

The visible acceptance tests passed and the held-out tests, which the agent never saw and
could not have satisfied by inspection, failed. This is the failure mode the fidelity
dimension exists to catch: the patch satisfies the suite and still misses the stated rule.

- baseline rep 0: acceptance passed but held-out tests failed -- the patch satisfies the visible suite and still misses the stated rule
- baseline rep 1: acceptance passed but held-out tests failed -- the patch satisfies the visible suite and still misses the stated rule
- baseline rep 4: acceptance passed but held-out tests failed -- the patch satisfies the visible suite and still misses the stated rule
- baseline rep 5: acceptance passed but held-out tests failed -- the patch satisfies the visible suite and still misses the stated rule
- baseline rep 6: acceptance passed but held-out tests failed -- the patch satisfies the visible suite and still misses the stated rule
- candidate rep 4: acceptance passed but held-out tests failed -- the patch satisfies the visible suite and still misses the stated rule
- candidate rep 7: acceptance passed but held-out tests failed -- the patch satisfies the visible suite and still misses the stated rule

Compare the patch against the ticket below, then read the held-out grader log for the trial.

## Trials

### baseline

| Rep | Status | acceptance | heldout | regressions | lint | types | Cost | Wall | Files | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | completed | [pass](../trials/notify-fallback/baseline/0/graders/acceptance.log) | [FAIL](../trials/notify-fallback/baseline/0/graders/heldout.log) | [pass](../trials/notify-fallback/baseline/0/graders/regressions.log) | [pass](../trials/notify-fallback/baseline/0/graders/lint.log) | [pass](../trials/notify-fallback/baseline/0/graders/types.log) | $0.0858 | 52.9s | 1 | [patch](../trials/notify-fallback/baseline/0/patch.diff), [transcript](../trials/notify-fallback/baseline/0/transcript.json) |
| 1 | completed | [pass](../trials/notify-fallback/baseline/1/graders/acceptance.log) | [FAIL](../trials/notify-fallback/baseline/1/graders/heldout.log) | [pass](../trials/notify-fallback/baseline/1/graders/regressions.log) | [pass](../trials/notify-fallback/baseline/1/graders/lint.log) | [pass](../trials/notify-fallback/baseline/1/graders/types.log) | $0.0850 | 60.6s | 1 | [patch](../trials/notify-fallback/baseline/1/patch.diff), [transcript](../trials/notify-fallback/baseline/1/transcript.json) |
| 2 | completed | [pass](../trials/notify-fallback/baseline/2/graders/acceptance.log) | [pass](../trials/notify-fallback/baseline/2/graders/heldout.log) | [pass](../trials/notify-fallback/baseline/2/graders/regressions.log) | [FAIL](../trials/notify-fallback/baseline/2/graders/lint.log) | [pass](../trials/notify-fallback/baseline/2/graders/types.log) | $0.0877 | 46.6s | 1 | [patch](../trials/notify-fallback/baseline/2/patch.diff), [transcript](../trials/notify-fallback/baseline/2/transcript.json) |
| 3 | completed | [pass](../trials/notify-fallback/baseline/3/graders/acceptance.log) | [pass](../trials/notify-fallback/baseline/3/graders/heldout.log) | [pass](../trials/notify-fallback/baseline/3/graders/regressions.log) | [pass](../trials/notify-fallback/baseline/3/graders/lint.log) | [pass](../trials/notify-fallback/baseline/3/graders/types.log) | $0.0958 | 74.2s | 1 | [patch](../trials/notify-fallback/baseline/3/patch.diff), [transcript](../trials/notify-fallback/baseline/3/transcript.json) |
| 4 | completed | [pass](../trials/notify-fallback/baseline/4/graders/acceptance.log) | [FAIL](../trials/notify-fallback/baseline/4/graders/heldout.log) | [pass](../trials/notify-fallback/baseline/4/graders/regressions.log) | [pass](../trials/notify-fallback/baseline/4/graders/lint.log) | [pass](../trials/notify-fallback/baseline/4/graders/types.log) | $0.0946 | 63.0s | 1 | [patch](../trials/notify-fallback/baseline/4/patch.diff), [transcript](../trials/notify-fallback/baseline/4/transcript.json) |
| 5 | completed | [pass](../trials/notify-fallback/baseline/5/graders/acceptance.log) | [FAIL](../trials/notify-fallback/baseline/5/graders/heldout.log) | [pass](../trials/notify-fallback/baseline/5/graders/regressions.log) | [pass](../trials/notify-fallback/baseline/5/graders/lint.log) | [pass](../trials/notify-fallback/baseline/5/graders/types.log) | $0.0986 | 86.2s | 1 | [patch](../trials/notify-fallback/baseline/5/patch.diff), [transcript](../trials/notify-fallback/baseline/5/transcript.json) |
| 6 | completed | [pass](../trials/notify-fallback/baseline/6/graders/acceptance.log) | [FAIL](../trials/notify-fallback/baseline/6/graders/heldout.log) | [pass](../trials/notify-fallback/baseline/6/graders/regressions.log) | [pass](../trials/notify-fallback/baseline/6/graders/lint.log) | [pass](../trials/notify-fallback/baseline/6/graders/types.log) | $0.0795 | 58.9s | 1 | [patch](../trials/notify-fallback/baseline/6/patch.diff), [transcript](../trials/notify-fallback/baseline/6/transcript.json) |
| 7 | completed | [pass](../trials/notify-fallback/baseline/7/graders/acceptance.log) | [pass](../trials/notify-fallback/baseline/7/graders/heldout.log) | [pass](../trials/notify-fallback/baseline/7/graders/regressions.log) | [pass](../trials/notify-fallback/baseline/7/graders/lint.log) | [pass](../trials/notify-fallback/baseline/7/graders/types.log) | $0.0949 | 77.5s | 1 | [patch](../trials/notify-fallback/baseline/7/patch.diff), [transcript](../trials/notify-fallback/baseline/7/transcript.json) |

- rep 0: 1 permission denial(s) : the agent was blocked from a tool it tried to use
- rep 0 touched: `src/notifier/service.py`
- rep 1: 1 permission denial(s) : the agent was blocked from a tool it tried to use
- rep 1 touched: `src/notifier/service.py`
- rep 2 touched: `src/notifier/service.py`
- rep 3 touched: `src/notifier/service.py`
- rep 4 touched: `src/notifier/service.py`
- rep 5 touched: `src/notifier/service.py`
- rep 6 touched: `src/notifier/service.py`
- rep 7 touched: `src/notifier/service.py`

### candidate

| Rep | Status | acceptance | heldout | regressions | lint | types | Cost | Wall | Files | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | completed | [pass](../trials/notify-fallback/candidate/0/graders/acceptance.log) | [pass](../trials/notify-fallback/candidate/0/graders/heldout.log) | [pass](../trials/notify-fallback/candidate/0/graders/regressions.log) | [pass](../trials/notify-fallback/candidate/0/graders/lint.log) | [pass](../trials/notify-fallback/candidate/0/graders/types.log) | $0.1261 | 75.2s | 1 | [patch](../trials/notify-fallback/candidate/0/patch.diff), [transcript](../trials/notify-fallback/candidate/0/transcript.json) |
| 1 | completed | [pass](../trials/notify-fallback/candidate/1/graders/acceptance.log) | [pass](../trials/notify-fallback/candidate/1/graders/heldout.log) | [pass](../trials/notify-fallback/candidate/1/graders/regressions.log) | [pass](../trials/notify-fallback/candidate/1/graders/lint.log) | [pass](../trials/notify-fallback/candidate/1/graders/types.log) | $0.1420 | 92.0s | 1 | [patch](../trials/notify-fallback/candidate/1/patch.diff), [transcript](../trials/notify-fallback/candidate/1/transcript.json) |
| 2 | completed | [pass](../trials/notify-fallback/candidate/2/graders/acceptance.log) | [pass](../trials/notify-fallback/candidate/2/graders/heldout.log) | [pass](../trials/notify-fallback/candidate/2/graders/regressions.log) | [pass](../trials/notify-fallback/candidate/2/graders/lint.log) | [pass](../trials/notify-fallback/candidate/2/graders/types.log) | $0.1138 | 66.4s | 1 | [patch](../trials/notify-fallback/candidate/2/patch.diff), [transcript](../trials/notify-fallback/candidate/2/transcript.json) |
| 3 | completed | [pass](../trials/notify-fallback/candidate/3/graders/acceptance.log) | [pass](../trials/notify-fallback/candidate/3/graders/heldout.log) | [pass](../trials/notify-fallback/candidate/3/graders/regressions.log) | [pass](../trials/notify-fallback/candidate/3/graders/lint.log) | [pass](../trials/notify-fallback/candidate/3/graders/types.log) | $0.0879 | 52.3s | 1 | [patch](../trials/notify-fallback/candidate/3/patch.diff), [transcript](../trials/notify-fallback/candidate/3/transcript.json) |
| 4 | completed | [pass](../trials/notify-fallback/candidate/4/graders/acceptance.log) | [FAIL](../trials/notify-fallback/candidate/4/graders/heldout.log) | [pass](../trials/notify-fallback/candidate/4/graders/regressions.log) | [pass](../trials/notify-fallback/candidate/4/graders/lint.log) | [pass](../trials/notify-fallback/candidate/4/graders/types.log) | $0.1179 | 83.3s | 1 | [patch](../trials/notify-fallback/candidate/4/patch.diff), [transcript](../trials/notify-fallback/candidate/4/transcript.json) |
| 5 | completed | [pass](../trials/notify-fallback/candidate/5/graders/acceptance.log) | [pass](../trials/notify-fallback/candidate/5/graders/heldout.log) | [pass](../trials/notify-fallback/candidate/5/graders/regressions.log) | [pass](../trials/notify-fallback/candidate/5/graders/lint.log) | [pass](../trials/notify-fallback/candidate/5/graders/types.log) | $0.1191 | 96.8s | 1 | [patch](../trials/notify-fallback/candidate/5/patch.diff), [transcript](../trials/notify-fallback/candidate/5/transcript.json) |
| 6 | completed | [pass](../trials/notify-fallback/candidate/6/graders/acceptance.log) | [pass](../trials/notify-fallback/candidate/6/graders/heldout.log) | [pass](../trials/notify-fallback/candidate/6/graders/regressions.log) | [pass](../trials/notify-fallback/candidate/6/graders/lint.log) | [pass](../trials/notify-fallback/candidate/6/graders/types.log) | $0.1078 | 77.0s | 1 | [patch](../trials/notify-fallback/candidate/6/patch.diff), [transcript](../trials/notify-fallback/candidate/6/transcript.json) |
| 7 | completed | [pass](../trials/notify-fallback/candidate/7/graders/acceptance.log) | [FAIL](../trials/notify-fallback/candidate/7/graders/heldout.log) | [pass](../trials/notify-fallback/candidate/7/graders/regressions.log) | [pass](../trials/notify-fallback/candidate/7/graders/lint.log) | [pass](../trials/notify-fallback/candidate/7/graders/types.log) | $0.1138 | 77.0s | 1 | [patch](../trials/notify-fallback/candidate/7/patch.diff), [transcript](../trials/notify-fallback/candidate/7/transcript.json) |

- rep 0 touched: `src/notifier/service.py`
- rep 1 touched: `src/notifier/service.py`
- rep 2 touched: `src/notifier/service.py`
- rep 3 touched: `src/notifier/service.py`
- rep 4 touched: `src/notifier/service.py`
- rep 5 touched: `src/notifier/service.py`
- rep 6 touched: `src/notifier/service.py`
- rep 7 touched: `src/notifier/service.py`

## The ticket the agent was given

Identical for both arms. The only difference between them is the harness.

- baseline: [prompt](../trials/notify-fallback/baseline/0/prompt.txt), [invocation](../trials/notify-fallback/baseline/0/command.txt)
- candidate: [prompt](../trials/notify-fallback/candidate/0/prompt.txt), [invocation](../trials/notify-fallback/candidate/0/command.txt)

Diff the two `prompt.txt` files to confirm the arms received the same instruction; diff the
two `command.txt` files to see exactly what differed between the harnesses.

## What to check by hand

- [ ] Read a patch from each arm. Do they differ in ways the graders cannot see?
- [ ] Where a grader failed, does its log show a real defect or a broken grader?
- [ ] Where both arms passed, is either patch something you would reject at review?

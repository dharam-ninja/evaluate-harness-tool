# `html-contact`

[← back to the report](../report.md)

**Baseline fail -> Candidate pass (**IMPROVED**)**

## Trials

### baseline

| Rep | Status | acceptance | heldout | regressions | validator | Cost | Wall | Files | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| 0 | completed | [FAIL](../trials/html-contact/baseline/0/graders/acceptance.log) | [FAIL](../trials/html-contact/baseline/0/graders/heldout.log) | [pass](../trials/html-contact/baseline/0/graders/regressions.log) | [pass](../trials/html-contact/baseline/0/graders/validator.log) | $0.0000 | 26.8s | 1 | [patch](../trials/html-contact/baseline/0/patch.diff), [transcript](../trials/html-contact/baseline/0/transcript.json) |
| 1 | completed | [FAIL](../trials/html-contact/baseline/1/graders/acceptance.log) | [FAIL](../trials/html-contact/baseline/1/graders/heldout.log) | [pass](../trials/html-contact/baseline/1/graders/regressions.log) | [pass](../trials/html-contact/baseline/1/graders/validator.log) | $0.0000 | 16.0s | 1 | [patch](../trials/html-contact/baseline/1/patch.diff), [transcript](../trials/html-contact/baseline/1/transcript.json) |
| 2 | completed | [FAIL](../trials/html-contact/baseline/2/graders/acceptance.log) | [FAIL](../trials/html-contact/baseline/2/graders/heldout.log) | [pass](../trials/html-contact/baseline/2/graders/regressions.log) | [pass](../trials/html-contact/baseline/2/graders/validator.log) | $0.0000 | 14.1s | 1 | [patch](../trials/html-contact/baseline/2/patch.diff), [transcript](../trials/html-contact/baseline/2/transcript.json) |
| 3 | completed | [FAIL](../trials/html-contact/baseline/3/graders/acceptance.log) | [FAIL](../trials/html-contact/baseline/3/graders/heldout.log) | [pass](../trials/html-contact/baseline/3/graders/regressions.log) | [pass](../trials/html-contact/baseline/3/graders/validator.log) | $0.0000 | 13.3s | 1 | [patch](../trials/html-contact/baseline/3/patch.diff), [transcript](../trials/html-contact/baseline/3/transcript.json) |

- rep 0 touched: `index.html`
- rep 1 touched: `index.html`
- rep 2 touched: `index.html`
- rep 3 touched: `index.html`

### candidate

| Rep | Status | acceptance | heldout | regressions | validator | Cost | Wall | Files | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| 0 | completed | [pass](../trials/html-contact/candidate/0/graders/acceptance.log) | [pass](../trials/html-contact/candidate/0/graders/heldout.log) | [pass](../trials/html-contact/candidate/0/graders/regressions.log) | [pass](../trials/html-contact/candidate/0/graders/validator.log) | $0.1385 | 44.5s | 1 | [patch](../trials/html-contact/candidate/0/patch.diff), [transcript](../trials/html-contact/candidate/0/transcript.json) |
| 1 | completed | [pass](../trials/html-contact/candidate/1/graders/acceptance.log) | [pass](../trials/html-contact/candidate/1/graders/heldout.log) | [pass](../trials/html-contact/candidate/1/graders/regressions.log) | [pass](../trials/html-contact/candidate/1/graders/validator.log) | $0.1274 | 33.5s | 1 | [patch](../trials/html-contact/candidate/1/patch.diff), [transcript](../trials/html-contact/candidate/1/transcript.json) |
| 2 | completed | [pass](../trials/html-contact/candidate/2/graders/acceptance.log) | [pass](../trials/html-contact/candidate/2/graders/heldout.log) | [pass](../trials/html-contact/candidate/2/graders/regressions.log) | [pass](../trials/html-contact/candidate/2/graders/validator.log) | $0.1631 | 42.5s | 1 | [patch](../trials/html-contact/candidate/2/patch.diff), [transcript](../trials/html-contact/candidate/2/transcript.json) |
| 3 | completed | [pass](../trials/html-contact/candidate/3/graders/acceptance.log) | [pass](../trials/html-contact/candidate/3/graders/heldout.log) | [pass](../trials/html-contact/candidate/3/graders/regressions.log) | [pass](../trials/html-contact/candidate/3/graders/validator.log) | $0.1580 | 40.3s | 1 | [patch](../trials/html-contact/candidate/3/patch.diff), [transcript](../trials/html-contact/candidate/3/transcript.json) |

- rep 0 touched: `index.html`
- rep 1 touched: `index.html`
- rep 2 touched: `index.html`
- rep 3 touched: `index.html`

## The ticket the agent was given

Identical for both arms. The only difference between them is the harness.

- baseline: [prompt](../trials/html-contact/baseline/0/prompt.txt), [invocation](../trials/html-contact/baseline/0/command.txt)
- candidate: [prompt](../trials/html-contact/candidate/0/prompt.txt), [invocation](../trials/html-contact/candidate/0/command.txt)

Diff the two `prompt.txt` files to confirm the arms received the same instruction; diff the
two `command.txt` files to see exactly what differed between the harnesses.

## What to check by hand

- [ ] Read a patch from each arm. Do they differ in ways the graders cannot see?
- [ ] Where a grader failed, does its log show a real defect or a broken grader?
- [ ] Where both arms passed, is either patch something you would reject at review?

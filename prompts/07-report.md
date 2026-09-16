Read PLAN.md §4. Implement report.py and both jinja2 templates while the Phase 6 run
executes. Render from whatever partial trials exist. The report must handle incomplete data
without crashing, because that is how you will iterate on it.

report.md:
- header: candidate vs baseline, run id, date, task/rep counts
- recommendation AND the condition that fired, read from comparator's exported rule
- dimension table, baseline -> candidate
- per-task transition table, PASS -> FAIL visually prominent
- a separate UNSTABLE section, never folded into the counts
- cost figures carrying "successful trials only" on the same line as the number
- a manual checklist for business fidelity: an empty checklist a human fills in
- a banner when jobs > 1 stating wall-clock is unreliable

Every aggregate claim links to a relative path: tasks/<task>.md, a patch.diff, or a
graders/<id>.log. An aggregate number with no link is a bug in this phase.

report.json: the same content as data, structured so a consumer can recompute the
recommendation from it.

Gate: `harness-eval report runs/<id>` renders. Follow three links by hand; each must land on
a real file that supports the claim above it.

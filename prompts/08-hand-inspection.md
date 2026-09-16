The run is complete. Do not touch the report layer yet. Spend this phase reading output and
disbelieving it. This produces DESIGN.md §4, which cannot be written from a template.

Read by hand:
1. Both arms' patch.diff for fix-rounding. Does the verdict match what the code does? Did
   anything pass acceptance and fail held-out, and is the patch wrong in the way held-out
   claims?
2. Any UNSTABLE task, both reps' patches. Genuine non-determinism, or is the evaluator
   producing different conditions across reps: leaked state, a timeout counted as failure,
   a flaky grader?
3. The cheapest and most expensive trials. Is the cost gap real work, or did a cheap trial
   crash early or time out?
4. One PASS -> PASS task. Does the candidate patch actually differ, or is "unchanged
   success" hiding a quality difference no grader can see?

For each finding write in NOTES.md: what the tool reported, what the code actually does, and
whether the tool was wrong or the task was wrong. Both are real answers.

Fix only what the inspection justifies, then re-render with `harness-eval report runs/<id>`.
Do not re-run the agents. The run/report split exists for exactly this moment.

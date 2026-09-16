Read PLAN.md §2 and §4. Implement graders.py and wire it into the run.

CommandGrader: one class, no per-language logic:
- run grader.command in the finished workspace, inheriting its venv
- capture exit code, stdout/stderr tail, duration -> graders/<id>.log
- exit 0 = pass, else fail; timeout = fail with a distinct reason string

The held-out overlay is the part that matters:
- for a grader with `overlay: heldout`, copy task.heldout_tests into the workspace at
  tests/heldout/ AFTER the agent has exited, then run the command
- assert the overlay path did not exist before the copy. If it did, the agent saw the
  held-out tests and the fidelity signal for that trial is void, so fail loudly rather than
  emit a passing number you cannot trust.
- the overlay must land after patch.diff is taken, or the patch will contain tests the
  agent never wrote

tests/test_graders.py: exit-code mapping; timeout yields fail-with-reason, not a crash;
overlay lands correctly; overlay can never precede the agent run.

Gate: the Phase 3 trial now produces 5 grader logs. By hand: the heldout log runs tests the
agent could not have seen, and patch.diff does not contain them.

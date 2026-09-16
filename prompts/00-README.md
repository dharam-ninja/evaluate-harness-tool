# Prompts used to build this tool

Each file is a prompt given to the coding agent, in the order it was used. They were
written up front as a phase plan (see `../PLAN.md`), then pasted one per session.

Where a phase was skipped or a prompt was wrong, that is recorded here rather than
tidied away. The sequence below is what actually happened, not what was planned.

| # | Phase | Outcome |
|---|---|---|
| 01 | Ground truth: verify the CLI before designing around it | 5 of the brief's flag claims were wrong |
| 02 | Demo repo + the deliberately weak acceptance suite | trap verified before spending |
| 03 | Runner: isolation, adapter, evidence | Phase 2's modules had to be built here first |
| 04 | Graders + the held-out overlay | found the venv PATH bug |
| 05 | Comparator: transitions, UNSTABLE, the recommendation rule | 100% branch coverage |
| 06 | Task suite + launch the full run | two probe trials caught two real bugs |
| 07 | Report layer | every task-page link was broken |
| 08 | Hand inspection: disbelieve the output | produced DESIGN.md §4 |
| 09 | Docs and packaging | this file |

Phase 2 was never pasted; its modules were built inside phase 3 because `run` cannot be
wired without them. That is why the numbering has a gap in the transcript.

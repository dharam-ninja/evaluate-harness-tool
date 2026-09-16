Read PLAN.md §3 and §10, then establish ground truth about this machine before any design
depends on it. Write no implementation code this phase.

1. Install and authenticate the Claude Code CLI. Confirm `claude --version` resolves in
   PowerShell, not only in git-bash.
2. Run `claude --help`. Record verbatim in NOTES.md which of these actually exist:
   -p, --output-format json, --model, --add-dir, --settings, --bare,
   --no-session-persistence, --max-budget-usd, --fallback-model.
   PLAN.md §3 lists these as ASSERTED BY THE BRIEF, NOT VERIFIED. Mark each CONFIRMED or
   ABSENT. Do not assume.
3. Run: claude -p "reply with the word ok" --output-format json
   Save the raw response to NOTES.md. Identify exactly which JSON fields carry cost, token
   counts, turn count and duration. Those field names are what evidence.py will parse.
4. Create a venv, `pip install -e ".[dev]"`, confirm `harness-eval --help` fails with an
   ImportError from the cli.py stub rather than a packaging error.
5. Time one trivial `claude -p` call end to end.

Gate: NOTES.md holds a CONFIRMED/ABSENT line per flag, one raw JSON response, one measured
duration. Report every PLAN.md assumption that is now false.

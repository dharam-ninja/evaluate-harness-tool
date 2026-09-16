Read PLAN.md §7 and §8. Ship the submission. No new features.

1. Commit the sample run: git add -f runs/<id> and its rendered report. Verify on a CLEAN
   clone, timed: pip install -e . && harness-eval report runs/<id> yields the report in
   under five minutes with no agent CLI and no API key. If it does not, fix the README, not
   the claim.

2. README.md: quick start with the OFFLINE sample run first, since most reviewers will not have
   the CLI authenticated, then the real run, then what the report means, then config.

3. DESIGN.md, ONE PAGE, HARD LIMIT. Write §4 from the NOTES.md hand-inspection entries,
   never from a guess. If the inspection produced no distrust case, say what you inspected
   and what held up; the requirement explicitly warns against fabricating this.

4. PROCESS.md, prompts/, transcripts/: copy the session transcript, render it readable, do
   not trim it. Index the prompts in order. Summarise the NOTES.md hand-checks with links.

5. Final: pytest, ruff check ., mypy src green on the evaluator itself.

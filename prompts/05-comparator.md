Read PLAN.md §4, "Comparator rules". Implement comparator.py. The tool's defensibility lives
here: these rules get printed in the report, so they must be exactly the rules the code runs.

Implement verbatim from §4: per-harness outcome across reps (PASS/FAIL/UNSTABLE);
transition; dimension rollups; the recommendation rule in its stated precedence order;
confidence LOW if reps < 2 or any task UNSTABLE, else MODERATE, never HIGH.

Two rules that are easy to get subtly wrong:
- UNSTABLE is excluded from improvement and regression counts. Do not round it to PASS or
  FAIL. Refusing to round is half this tool's credibility.
- cost deltas cover SUCCESSFUL trials only. A candidate that fails fast is cheaper and
  worse; averaging failures into cost rewards that.

Export the rule as data, an ordered list of (condition_name, predicate), so report.py
prints which condition fired instead of restating the rule in a template.

tests/test_comparator.py: a truth table, one case per branch, including "improvements > 0
but a regression exists" -> NEGATIVE, and an all-UNSTABLE suite -> INCONCLUSIVE + LOW.

Gate: pytest green and every branch of the §4 rule covered.

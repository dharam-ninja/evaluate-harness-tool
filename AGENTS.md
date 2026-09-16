# AGENTS.md: instructions for the agent building this tool

> Not to be confused with `examples/harnesses/*/AGENTS.md`, which are the files **under
> test** in the experiments. This one governs work on the evaluator itself.

## Project

`harness-eval` runs the same engineering tasks against a baseline and a candidate
coding-agent harness under controlled conditions, and produces an inspectable report.

Domain model, in `models.py`: `Task`, `AgentHarness`, `Trial`, `Grader`, `TaskComparison`,
`EvaluationReport`. Those names come from Anthropic's "Demystifying evals for AI agents" and
are the tool's vocabulary. Use them, do not invent synonyms.

## Conventions

- Python 3.10, full type annotations, `mypy --strict` clean.
- Docstrings on every module and public function. `ruff` enforces it.
- Comments explain *why*, never *what*. A comment restating the code is noise.
- pydantic v2 for anything that crosses a file boundary.

## Commands

```
pytest -q                  # the evaluator's own tests
ruff check src tests
mypy src
harness-eval validate examples/eval.yaml
```

All three must be green. A tool that grades convention compliance and fails its own lint is
not defensible.

## Rules

- **Never hardcode a grader id, dimension name or task id in Python.** Adding any of them is
  a YAML edit. `config.py` validates against the config's own declared vocabulary.
- **`run` never renders; `report` never runs trials.** Trials cost money; rendering does not.
- **The held-out overlay lands after `patch.diff` is captured.** Otherwise the patch contains
  tests the agent never wrote.
- **Absent evidence is `None`, never `0`.** A zero cost is indistinguishable from a free run.
- **Do not round `UNSTABLE`.** If reps disagree, say so and exclude it from the counts.
- Never weaken a test to make a run pass. If a grader fails, find out why first.
- Do not modify a task, grader or config after seeing results in order to change the answer.

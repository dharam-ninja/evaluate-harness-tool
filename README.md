# Submission

Please find below the summary of the harness evaluation tool I built as part of the take-home challenge.

**Repository:** https://github.com/dharam-ninja/evaluate-harness-tool/

## Overview

When changing a coding agent setup, such as switching models, adding instructions, introducing guardrails, or modifying workflows, it is difficult to measure whether the change actually improves results.

This tool provides a structured evaluation process to compare harness changes using measurable evidence instead of assumptions.

## What it does

The tool:

* Runs the same task using two different harness configurations ('baseline' and 'candidate') multiple times in isolated workspaces.

* Evaluates each trial using four types of checks:

  * **Acceptance checks**: verifies whether the agent completed the requested task.
  * **Held-out checks**: runs hidden tests after capturing the agent output to measure correctness beyond visible requirements.
  * **Regression checks**: verifies that existing functionality was not broken.
  * **Validator checks**: validates whether the generated output follows the expected format.

* Compares both harness configurations and generates a report showing:

  * Improvements
  * Regressions
  * Results where confidence is low due to inconsistent runs

A single command runs the complete evaluation workflow:

```
harness-eval evaluate <config.yaml>
```

The command executes the trials and generates:

* `report.md` for a human-readable summary
* `report.json` for machine-readable results

Each reported result is linked back to the original artifacts, making the evaluation traceable and reproducible.

## Deliverables

### 1. Repository and README

Complete implementation with setup instructions and a runnable example:

[README.md](README.md)

### 2. Evaluation Reports

Example evaluation report showing harness comparison results:

[runs/mixed-01/report.md](runs/mixed-01/report.md)

### 3. Evaluate Command

Single command workflow from configuration to final report:

README command reference: [README.md#4-command-reference](README.md#4-command-reference)

CLI implementation: [src/harness_eval/cli.py](src/harness_eval/cli.py)

### 4. Design Document

The design document covers:

* Architecture and key concepts
* Major engineering decisions
* Trade-offs and scope decisions
* A result that was not considered reliable due to insufficient confidence

[DESIGN.md](DESIGN.md)

### 5. Process Artifacts

Documentation covering:

* Build instructions
* Agent instructions
* Development process
* Prompts used during implementation
* Manual validation notes

Build instructions and process documentation:

[AGENTS.md](AGENTS.md)

[PROCESS.md](PROCESS.md)

Prompt history:

[prompts/](prompts/)

Key prompts:

* [prompts/00-README.md](prompts/00-README.md)
* [prompts/01-ground-truth.md](prompts/01-ground-truth.md)
* [prompts/04-graders.md](prompts/04-graders.md)
* [prompts/05-comparator.md](prompts/05-comparator.md)
* [prompts/07-report.md](prompts/07-report.md)
* [prompts/08-hand-inspection.md](prompts/08-hand-inspection.md)
* [prompts/09-docs-and-packaging.md](prompts/09-docs-and-packaging.md)

## Worked Example: mixed-01

The repository includes a complete runnable example that can be reproduced from committed data without requiring API keys or additional cost.

### Harness comparison

**Harness 1**

* Local SmolLM2 360M model
* No additional guidance file

**Harness 2**

* Claude Sonnet model
* Includes an `AGENTS.md` instruction file

### Result

Task evaluated: `html-contact`

Results:

* Harness 1: Failed (0/4 successful trials)
* Harness 2: Passed (4/4 successful trials)

The results were consistent across all repetitions without flaky behaviour.

The evaluation showed that Harness 2 produced better results for this task based on acceptance checks, hidden tests, and consistency across runs.

I would be happy to walk through the architecture, implementation details, and design decisions during the discussion.

---

# harness-eval

Paired baseline-vs-candidate evaluation for coding-agent harness changes.

You change one thing about how your agent works (`AGENTS.md`, a hook, the model, an MCP
server) and you need to know whether that change made engineering outcomes better before
rolling it out to everyone. This runs the same tasks against both configurations under
controlled conditions and produces an inspectable report, not a score.

---

## 1. Install

Requires Python 3.10+. Nothing else for the offline path.

**cmd.exe**

```
cd harness-eval
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

**PowerShell**

```
cd harness-eval
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

**bash / macOS / Linux**

```
cd harness-eval
python -m venv .venv
source .venv/bin/activate         # Windows git-bash: source .venv/Scripts/activate
pip install -e ".[dev]"
```

> **Activate the venv.** Without it `.venv\Scripts\python.exe` works in cmd but
> `.venv/Scripts/python.exe` does not, because cmd cannot execute a path written with forward
> slashes, and PowerShell needs a leading `.\`. Activating once removes the problem
> everywhere, and every command below assumes it.

---

## 2. Run it on a real example: 60 seconds, no API key, no spend

A complete 8-trial run is committed to this repository. Render it:

```
harness-eval report runs/mixed-01
```

```
POSITIVE SIGNAL - MODERATE confidence (rule: improved_without_regressing)
  1 improved, 0 regressed, 0 unstable, 0 unmeasured

  runs\mixed-01\report.md
  runs\mixed-01\report.json
```

Open **`runs/mixed-01/report.md`**. Then follow a link from it. Every number points at the
patch, transcript or grader log behind it.

### What that run compared

Task: *create an `index.html` contact page with a heading, name and email fields, a message
textarea and a submit button: semantic, accessible, valid HTML5, preserving existing
project conventions.* Identical prompt for both arms, byte-for-byte.

| | Harness 1 | Harness 2 |
|---|---|---|
| Model | `smollm2:360m` (local, Ollama) | `claude-sonnet-5` |
| Guidance | no `AGENTS.md` | `AGENTS.md` provided |
| Runner | single-shot script | Claude Code agentic loop |
| Trials | 4 | 4 |

### The result

```
                          Harness 1        Harness 2
acceptance  (7 tests)     0/4 trials       4/4 trials
held-out   (15 tests)     0/4 trials       4/4 trials
regression  (4 tests)     4/4 trials       4/4 trials
validator                 4/4 trials       4/4 trials
steps / runtime / cost    1 / 18s / $0.00  12 / 40s / $0.1468
```

Harness 1 copied the existing `about.html` almost verbatim (correct doctype, stylesheet
and footer, heading still reading "About Northwind Bakery") and added no form at all.
Identical in all four trials.

It still passed **22 of 27 individual checks**. Every one it passed only required *not
breaking anything*; every one it failed required *doing the work*. That gap is exactly why
the report keeps four dimensions instead of printing one percentage.



---

## 3. Run your own experiment

### What you need, and what each thing unlocks

Section 2 needs nothing but Python. Running live trials needs more, and the table says
exactly how much:

| You have | You can run |
|---|---|
| Python 3.10+ | `report` and `validate`. All of section 2, no spend. |
| Plus Node.js and a paid Claude account | every config except `mixed-01`'s local arm |
| Plus Ollama and `smollm2:360m` | `mixed-01` exactly as committed |

Live trials cost real money and bill to your own account. Budget roughly **$0.15 per trial**;
the committed 8-trial `mixed-01` run cost **$0.59**.

### Prerequisites for a live run

**A. Python 3.10+ and this package** (section 1, if you have not already)

```
python --version                  # expect 3.10 or newer
pip install -e ".[dev]"
harness-eval --help
```

**B. Node.js 18+**

Claude Code is distributed through npm, so Node comes first. Download it from
<https://nodejs.org> or use a package manager:

```
winget install OpenJS.NodeJS.LTS     # Windows
brew install node                    # macOS
```

```
node --version                    # expect v18 or newer
npm --version
```

**C. Claude Code, logged in**

```
npm install -g @anthropic-ai/claude-code
claude                            # log in once, interactively, then exit
claude --version                  # expect 2.1.x
```

Authentication uses the OAuth session that login creates. No API key is set or requested,
and trials bill against that account.

**You need a paid Claude plan or API credit.** A free account authenticates but cannot run
trials. If you hold an API key rather than a subscription, pass it per harness instead of
logging in:

```yaml
    env: {ANTHROPIC_AUTH_TOKEN: "${MY_API_KEY}"}
```

Set `MY_API_KEY` in your shell before running. The `${...}` form keeps the secret out of
the config file, so the config stays safe to commit.

> **The resolved value is written into `runs/<id>/manifest.json`.** Config expansion happens
> at load time and the manifest records each harness verbatim, key included. If you use
> `env` for a credential, treat that run directory as secret: do not commit it, and do not
> re-include it in `.gitignore`. Logging in with `claude` avoids this entirely, which is why
> it is the documented default.

**D. Ollama and the local model** (only needed to reproduce `mixed-01`)

Install Ollama first. The commands below assume it is on your PATH:

```
winget install Ollama.Ollama                    # Windows
brew install ollama                             # macOS
curl -fsSL https://ollama.com/install.sh | sh   # Linux
```

Then pull the model and start the server:

```
ollama pull smollm2:360m          # ~700 MB
ollama serve                      # OpenAI-compatible on localhost:11434
```

**Verify the whole chain before spending anything:**

```
python --version                                  # 3.10+
node --version                                    # v18+
claude --version                                  # 2.1.x
curl http://localhost:11434/api/tags              # lists smollm2:360m
harness-eval report runs/mixed-01                 # renders offline, proves the install
```

If the last command prints a recommendation, the tool is installed correctly and only the
credentials remain to be exercised, which step 2 below does for ~$0.15.

### Step 1: see the plan, spend nothing

```
harness-eval validate examples/eval-mixed.yaml
```

```
  repo      ...\examples\demo-html
  harness   baseline   model=smollm2:360m     provider=http://localhost:11434/v1
  harness   candidate  model=claude-sonnet-5  provider=default (CLI-configured)
  tasks     html-contact
  graders   acceptance*, heldout*, regressions*, validator  (* = critical)
  variable  model, endpoint, command, instructions  (everything else must match)

1 tasks x 2 harnesses x 4 reps = 8 trials
```

Check the `variable` line before spending. It should name only what you meant to change.

### Step 2: one trial first

Always. It costs ~40 s and ~$0.15, and catches auth problems, permission problems and
config typos before you commit to a full run.

```
harness-eval run examples/eval-mixed.yaml --harness candidate --reps 1 --run-id smoke
```

```
  running html-contact/candidate/0 ...
    completed   44.5s  $0.1385  1 file(s)  1252B  acceptance heldout regressions validator
```

### Step 3: the full run

```
harness-eval run examples/eval-mixed.yaml --run-id my-run
```

8 trials, ~5 minutes, ~$0.59. Progress prints per trial.

### Step 4: render

```
harness-eval report runs/my-run
```

Re-run this as often as you like. It never re-runs trials, so fixing the report costs
seconds instead of money.

**Or steps 3 and 4 in one:** `harness-eval evaluate examples/eval-mixed.yaml`

---

## 4. Command reference

| Command | Purpose | Cost |
|---|---|---|
| `validate <config>` | Parse the config, print the trial matrix. Runs nothing. | free |
| `run <config>` | Execute trials, write evidence. Renders no report. | real |
| `report <run-dir>` | Render `report.md` + `report.json` from an existing run. | free |
| `evaluate <config>` | `run` then `report`. | real |

### `run` options

| Option | Does | Example |
|---|---|---|
| `--run-id <str>` | name the run directory; otherwise a timestamp | `--run-id my-run` |
| `--reps <int>` | override the config's rep count | `--reps 2` |
| `--task <id>` | run only one task | `--task html-contact` |
| `--harness <name>` | run only one arm, for smoke tests | `--harness candidate` |
| `--out <path>` | where run directories go (default `runs/`) | `--out /tmp/runs` |

**Why `run` and `report` are separate.** Trials cost money and are non-deterministic;
rendering is neither. During this project a session died mid-run. The expensive half was
lost, the rendering was never at risk.

---

## 5. The config behind the example

This is `examples/eval-mixed.yaml`, the file that produced `runs/mixed-01`. Harness 1 is
the local model with no guidance; Harness 2 is Claude Sonnet with it.

```yaml
# This comparison changes FOUR things at once, not one:
#   1. the model      smollm2:360m           vs  claude-sonnet-5
#   2. the provider   localhost              vs  Anthropic
#   3. the runner     a fixed 3-step script  vs  Claude Code's agentic loop
#   4. the guidance   absent                 vs  present
# Any difference therefore cannot be attributed to any one of them. All four are
# declared below so the manifest records the experiment honestly.

repo: examples/demo-html

intended_difference:                  # everything NOT listed must be identical
  - model
  - endpoint
  - command
  - instructions

harnesses:
  baseline:                           # HARNESS 1: local model, no AGENTS.md
    description: Harness 1 - smollm2:360m (local, Ollama), NO AGENTS.md
    command: >-
      python -m harness_eval.local_agent
      --endpoint ${LOCAL_MODEL_URL:-http://localhost:11434/v1}
      --model {model}
      --target index.html
      --verify "python validate.py"
      --max-rounds 2
    model: ${LOCAL_MODEL:-smollm2:360m}
    endpoint: ${LOCAL_MODEL_URL:-http://localhost:11434/v1}
    budget: 0.00                      # local inference is free
    instructions: null                # no guidance

  candidate:                          # HARNESS 2: Claude Sonnet, with AGENTS.md
    description: Harness 2 - claude-sonnet-5 (Anthropic), WITH AGENTS.md
    command: >-
      claude -p --output-format stream-json --verbose --model {model}
      --permission-mode acceptEdits --permission-prompts none
      --allowedTools "Bash(cd *)" "Bash(python *)" Read Edit Write Glob Grep
      --no-session-persistence --setting-sources project
      --max-budget-usd {budget}
    model: claude-sonnet-5
    endpoint: null                    # the CLI's own provider
    budget: 2.00
    instructions: examples/harnesses/candidate-html/AGENTS.md

reps: 4
timeout_s: 900
jobs: 1

tasks:
  - html-contact

dimensions: [correctness, fidelity, regression, conventions]

graders:
  - {id: acceptance,  command: "pytest -q tests/acceptance", critical: true,  dimension: correctness}
  - {id: heldout,     command: "pytest -q tests/heldout",    critical: true,  dimension: fidelity, overlay: heldout}
  - {id: regressions, command: "pytest -q tests/regression", critical: true,  dimension: regression}
  - {id: validator,   command: "python validate.py",         critical: false, dimension: conventions}
```

### Reading it

- **Each harness has its own `command`.** Claude Code refuses model ids it does not
  recognise, so it cannot drive a local model. Harness 1 goes through a small runner
  instead. The evaluator does not care: `ShellAgentAdapter` runs whatever command a harness
  declares.
- **`instructions`** is the `AGENTS.md` path. `null` means the file is genuinely absent
  from that arm's workspace, not merely unwritten.
- **`${VAR}` and `${VAR:-default}`** expand from the environment, so an endpoint or token
  is never committed. A variable with no value *and* no default is a hard error, so a
  half-configured run fails immediately rather than silently using the wrong provider.
- **`intended_difference`** is what makes the comparison auditable. Everything not listed
  must match, and everything listed must actually differ. The manifest records both, and
  `controlled` is only `true` when each holds.

### To make it a controlled experiment

Change one thing instead of four: give both arms the same `command`, the same `model` and
the same `endpoint`, and set `intended_difference: [instructions]`. Then a difference in
the results can be attributed to the guidance, because nothing else moved.

Adding a task, grader or harness is always a YAML edit, with no Python changes. `config.py`
rejects a grader whose `dimension` is not declared, and no grader id, dimension name or
task id appears anywhere in the code.

### Comparing two models instead

```yaml
intended_difference: [model, endpoint]

harnesses:
  baseline:
    model: ${HARNESS1_MODEL:-llama-3.3-70b-instruct}
    endpoint: ${HARNESS1_MODEL_URL}              # never written in the file
    env: {ANTHROPIC_AUTH_TOKEN: "${HARNESS1_API_KEY:-}"}
  candidate:
    model: claude-sonnet-5                        # no endpoint: the CLI's own provider
```

```
set HARNESS1_MODEL_URL=https://your-host/v1       rem cmd
$env:HARNESS1_MODEL_URL = "https://your-host/v1"  # PowerShell
export HARNESS1_MODEL_URL=https://your-host/v1    # bash
```

`${VAR}` and `${VAR:-default}` expand through every string. **A variable with no value and
no default is a hard error**, so a half-configured run fails immediately rather than
quietly falling back to the default provider and measuring one model twice.

---

## 6. Reading the report

- **Recommendation** plus the rule that produced it, printed from the same ordered list the
  code evaluates, so the policy and the verdict cannot drift apart.
- **Transitions** : `FAIL->PASS` improved, `PASS->FAIL` regressed, `UNSTABLE` excluded from
  the counts rather than rounded.
- **Four dimensions** with per-grader trial counts underneath, and `NOT SELF-CONSISTENT`
  where an arm disagreed with itself across reps.
- **Cost** over successful trials only, paired by task, with the prompt-cache caveat.
- **A business-fidelity checklist**, generated empty: the one part the tool refuses to
  answer.
- Confidence is never reported as HIGH.

### Where the evidence lives

```
runs/<id>/
  report.md report.json          the report, and the same content as data
  manifest.json                  every trial as data, plus the fairness record
  tasks/<task>.md                per-task drill-down, both arms, every rep
  trials/<task>/<arm>/<rep>/
    patch.diff                   exactly what the agent changed
    transcript.json              the agent's own envelope: model, cost, tokens, turns
    prompt.txt command.txt       what it was asked, and how it was invoked
    graders/<id>.log             each grader's command, exit code and output
  workspaces/                    the repo each agent worked in (gitignored)
```

### Checking the experiment was fair

Every run records a `fairness` block in `manifest.json`:

```json
"fairness": {
  "intended_difference": ["model", "endpoint", "command", "instructions"],
  "identical": {"budget": false, "env": true},
  "controlled": true
}
```

`controlled: true` means two things held: every field *not* declared as the variable was
identical, **and** every field declared as the variable actually differed. A "difference"
that is the same on both sides is a config mistake, not an experiment.

---

## 7. How a trial works

```
1. fresh workspace     copy the repo EXCLUDING .git, git init, one commit
2. apply the harness   AGENTS.md / .claude/ copied in BEFORE that commit,
                       so they never appear as the agent's own work
3. start the agent     a separate OS process, not this tool
4. capture             patch.diff, transcript, every tool call
5. overlay held-out    only now, after the patch is saved
6. run the graders     the evaluator runs them itself; agent claims are ignored
```

Trial N cannot read trial N-1's history. The agent never sees the held-out tests. If the
agent says "tests pass", that claim is not evidence. The evaluator runs them anyway.

### The tests in the committed example

| Group | Count | Visible to the agent? | File |
|---|---|---|---|
| Acceptance | 7 | yes, copied into the workspace | `examples/tasks/html-contact/acceptance/test_contact_page.py` |
| Held-out | 15 | **no**, added after the agent stops | `examples/heldout/html-contact/test_contact_heldout.py` |
| Regression | 4 | yes, already in the repo | `examples/demo-html/tests/regression/test_existing_pages.py` |
| Validator | 1 | yes, already in the repo | `examples/demo-html/validate.py` |

All 27 were written before the experiment ran. Nothing is generated during or after.

---

## 8. Development

```
pytest -q                 # 91 tests
ruff check src tests
mypy src
```

All green. A tool that grades convention compliance and fails its own lint is not
defensible.

**Preflights matter more than they look.** `preflight_*.py` scripts run before any trial
and prove the experiment can give a trustworthy answer: the task is solvable without the
guidance, a *different* correct solution also passes, a deliberately wrong one fails, the
held-out tests are absent from a fresh workspace, and the guidance leaks no answers. Each
is written against one experiment's config; copy the nearest one when you add your own.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `'.venv' is not recognized` | cmd cannot run a forward-slash path | activate the venv first (§1) |
| `'npm' is not recognized` | Node.js is not installed | install Node 18+ (§3B), then reopen the terminal |
| `'ollama' is not recognized` | Ollama is not installed, or PATH is stale | install it (§3D) and open a NEW terminal; on Windows it lands in `%LOCALAPPDATA%\Programs\Ollama` |
| Trials fail immediately on the Claude arm | free account, or no API credit | a paid plan or API credit is required (§3C); `claude --version` succeeding does not prove billing works |
| `config error ... not set and has no default` | a `${VAR}` has no value | set it, or write `${VAR:-fallback}` |
| Every `lint`/`types` grader fails | the grader's tool is not on PATH | the evaluator prepends its own venv; check the tool is installed there |
| `unrecognized_model` | Claude Code rejects non-Anthropic model ids | use `endpoint` with an Anthropic-compatible provider, or a different runner |
| Local arm fails instantly | Ollama not running | `ollama serve`, then check `http://localhost:11434/api/tags` |
| Trials time out | `timeout_s` too low for the task | raise it in the config; a killed trial records `TIMEOUT`, not `FAIL` |

---

## 10. Reading order

- **`DESIGN.md`** : one page: the concepts, the five hardest decisions, what was cut, and
  the result I did not trust.
- **`PROCESS.md`** : how this was built, what was checked by hand, where the agent was
  wrong.
- **`NOTES.md`** : the working log, written as it happened.
- **`PLAN.md`** : the phase plan written before any code.

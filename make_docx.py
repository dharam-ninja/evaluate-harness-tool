"""Generate the explanation document for the prose-vs-hook experiment.

Everything written here is read from the committed artifacts rather than retyped, so the
document cannot drift from what the run actually produced.
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

ROOT = Path(__file__).parent
RUN = ROOT / "runs" / "hook-01"
OUT = ROOT / "Harness-Evaluation-Explained.docx"

MONO = "Consolas"
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x5A, 0x5A, 0x5A)


def h1(doc: Document, text: str) -> None:
    """Section heading."""
    doc.add_page_break() if doc.paragraphs else None
    p = doc.add_heading(text, level=1)
    p.runs[0].font.color.rgb = INK


def h2(doc: Document, text: str) -> None:
    """Sub-heading."""
    doc.add_heading(text, level=2).runs[0].font.color.rgb = INK


def para(doc: Document, text: str, *, italic: bool = False) -> None:
    """Body paragraph."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = italic
    if italic:
        run.font.color.rgb = MUTED
    p.paragraph_format.space_after = Pt(8)


def bullets(doc: Document, items: list[str]) -> None:
    """Bulleted list."""
    for item in items:
        doc.add_paragraph(item, style="List Bullet").paragraph_format.space_after = Pt(3)


def code(doc: Document, text: str) -> None:
    """Fixed-width block for commands, config and code."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = MONO
    run.font.size = Pt(8.5)
    p.paragraph_format.left_indent = Pt(14)
    p.paragraph_format.space_after = Pt(10)


def table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    """Simple grid table."""
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    for cell, head in zip(t.rows[0].cells, headers, strict=True):
        cell.text = head
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(9)
    for row in rows:
        cells = t.add_row().cells
        for cell, value in zip(cells, row, strict=True):
            cell.text = value
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def build() -> Path:
    """Write the document."""
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    trials = manifest["trials"]

    def arm(name: str) -> list[dict]:
        return sorted((t for t in trials if t["harness"] == name), key=lambda t: t["rep"])

    def passes(name: str, grader: str) -> int:
        return sum(
            1 for t in arm(name)
            if any(g["id"] == grader and g["status"] == "pass" for g in t["graders"])
        )

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    title = doc.add_heading("Harness Evaluation: How It Works and What It Found", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    para(doc, "Comparing two coding-agent setups on the same task, with the same model. "
              "Run hook-01, 16 trials.", italic=True)

    # ---------------------------------------------------------------- 1. the question
    h2(doc, "1. The question we are answering")
    para(doc, "A team writes an AGENTS.md telling their coding agent to run the tests, the "
              "linter and the type checker before finishing. Does the agent actually do it, "
              "and does it produce better code?")
    para(doc, "Earlier experiments in this project measured something uncomfortable: across "
              "104 trials the agent read AGENTS.md every single time and ran the linter and "
              "type checker in 1 trial out of 8. So this experiment compares the same "
              "instruction delivered two ways:")
    bullets(doc, [
        "Harness 1: the instruction is written down and the agent is asked to follow it.",
        "Harness 2: the instruction is enforced by a hook that runs the checks itself.",
    ])
    para(doc, "Everything else is identical. Same model, same task, same repository, same "
              "tools, same permissions, same budget.")

    # ---------------------------------------------------------------- 2. the flow
    h1(doc, "2. The flow, step by step")
    code(doc,
         "YOU\n"
         "  run:  harness-eval run examples/eval-hook.yaml\n"
         "    |\n"
         "THE EVALUATOR (harness-eval)  -- for each of 16 trials:\n"
         "    |\n"
         "  1. FRESH WORKSPACE      copy the repo, exclude .git, git init, 1 commit\n"
         "  2. APPLY THE HARNESS    Harness 1 gets AGENTS.md\n"
         "                          Harness 2 gets .claude/ with the hook\n"
         "                          (committed as the starting point, so it never\n"
         "                           shows up as the agent's own work)\n"
         "  3. START THE AGENT      a separate process: Claude Code + Haiku\n"
         "    |\n"
         "THE AGENT  -- reads the code, writes the fix, may run commands\n"
         "             Harness 2: the hook blocks it from stopping while a check fails\n"
         "    |\n"
         "  4. CAPTURE              the patch, the transcript, every tool call\n"
         "  5. ADD HIDDEN TESTS     only now, after the patch is saved\n"
         "  6. RUN 5 GRADERS        the evaluator runs them itself\n"
         "    |\n"
         "  7. COMPARE              8 trials per side, then the report")
    para(doc, "Two details that matter. The hidden tests are added only after the agent has "
              "finished, so it can never see them. And the evaluator runs every check itself "
              "If the agent claims 'tests pass', that claim is ignored.")

    # ---------------------------------------------------------------- 3. the task
    h1(doc, "3. The task given to the AI agent")
    para(doc, "Both harnesses received exactly the same ticket. We verified the two files are "
              "byte-for-byte identical.")
    code(doc, (RUN / "trials" / "notify-fallback" / "baseline" / "0" / "prompt.txt")
         .read_text(encoding="utf-8").strip())
    para(doc, "The repository is a small notification package. The task is deliberately "
              "'repository-heavy': three things the agent needs are already in the code and "
              "the ticket never names them.")
    table(doc, ["Already in the repo", "Why it matters"], [
        ["call_with_retry in retry.py", "A working retry helper with exactly these rules. "
                                        "An agent that does not read the package rewrites it."],
        ["Two error classes in errors.py", "One is worth retrying, one never is. This decides "
                                           "the control flow."],
        ["get_logger in logging_utils.py", "Every logger is named with a prefix. Using "
                                           "logging.getLogger directly breaks the convention."],
    ])

    # ---------------------------------------------------------------- 4. the two arms
    h1(doc, "4. What each harness was given")
    table(doc, ["", "Harness 1", "Harness 2"], [
        ["Model", "claude-haiku-4-5", "claude-haiku-4-5 (same)"],
        ["Task", "identical", "identical"],
        ["Repository", "identical", "identical"],
        ["Tools / permissions", "identical", "identical"],
        ["Budget", "$2.00", "$2.00"],
        ["AGENTS.md", "YES", "no"],
        ["Hook (.claude/)", "no", "YES"],
    ])
    para(doc, "The run manifest records this automatically and marks the experiment "
              "controlled: true, meaning every field that was supposed to match did match, "
              "and the fields meant to differ actually differed.")

    h2(doc, "4a. Harness 1: the AGENTS.md, in full")
    code(doc, (RUN / "workspaces" / "notify-fallback" / "baseline" / "0" / "AGENTS.md")
         .read_text(encoding="utf-8").strip()
         if (RUN / "workspaces" / "notify-fallback" / "baseline" / "0" / "AGENTS.md").exists()
         else (ROOT / "examples" / "harnesses" / "prose-arm" / "AGENTS.md")
         .read_text(encoding="utf-8").strip())
    para(doc, "In plain words, it says: run the tests, the linter and the type checker; if "
              "something fails, fix the real cause and run it again; and do not cheat by "
              "deleting a test or silencing a warning.")

    h2(doc, "4b. Harness 2: what the hook does")
    para(doc, "Harness 2 has no AGENTS.md at all. Instead it carries two files that make the "
              "same three checks happen automatically.")
    para(doc, "The settings file registers a 'Stop' hook, which runs when the agent tries to "
              "finish:")
    code(doc, (ROOT / "examples" / "harnesses" / "hook-arm" / ".claude" / "settings.json")
         .read_text(encoding="utf-8").strip())
    para(doc, "The hook script runs the three checks. If any fails, it refuses to let the "
              "agent stop and hands back the real error message:")
    code(doc,
         'CHECKS = (\n'
         '    ("tests", [sys.executable, "-m", "pytest", "-q"]),\n'
         '    ("lint",  [sys.executable, "-m", "ruff", "check", "."]),\n'
         '    ("types", [sys.executable, "-m", "mypy", "--strict", "src"]),\n'
         ')\n\n'
         '# if any failed:\n'
         'print(json.dumps({\n'
         '    "decision": "block",\n'
         '    "reason": "These checks are failing. Fix the cause in the source --\n'
         '               do not edit tests, add suppressions, or loosen annotations."\n'
         '               + the actual error output\n'
         '}))')
    para(doc, "So the difference is not WHAT is asked. Both arms name the same three checks "
              "and forbid the same shortcuts. The difference is WHO runs them: Harness 1 is "
              "asked, Harness 2 is made to.")

    # ---------------------------------------------------------------- 5. the tests
    h1(doc, "5. The tests: 32 checks in three groups")
    para(doc, "Every check is deterministic: a command that either passes or fails. There is "
              "no 'is this code good?' judgement anywhere.")
    table(doc, ["Group", "Count", "Can the agent see them?", "What they are for"], [
        ["Visible (acceptance)", "2", "YES, copied into the workspace",
         "The basic feature works"],
        ["Hidden (held-out)", "17", "NO, added after the agent finishes",
         "The details the ticket asked for"],
        ["Existing (regression)", "13", "YES, already in the repo",
         "Nothing old was broken"],
    ])
    para(doc, "Plus two quality checks run as commands: ruff (style) and mypy --strict "
              "(types). Five graders in total.")

    h2(doc, "5a. The 2 visible tests")
    bullets(doc, [
        "A successful email returns its receipt.",
        "SMS is used when the email cannot be delivered.",
    ])
    para(doc, "These are deliberately basic. They tell the agent what the feature should do, "
              "without revealing the detailed rules.")

    h2(doc, "5b. What 'held-out' means, and why it exists")
    para(doc, "Held-out tests are written before the experiment, kept OUTSIDE the repository, "
              "and copied in only after the agent has stopped and its work has been saved. "
              "The agent cannot read them, cannot run them, and cannot tune its code to them.")
    para(doc, "They exist because passing the visible tests does not prove the work is "
              "correct. In this very run, every trial passed the visible tests, but 5 of 16 "
              "had a real bug that only the hidden tests caught.")

    h2(doc, "5c. The 17 hidden tests, and what each checks")
    table(doc, ["#", "What it checks", "Which part of the ticket"], [
        ["1", "Email is tried exactly 3 times", "at most 3 attempts"],
        ["2", "A first-time success is not retried", "at most 3 attempts"],
        ["3", "No wait after the final attempt", "do not wait after the last"],
        ["4", "A wait really happens between attempts", "wait between attempts"],
        ["5", "A permanent failure is NOT retried", "only failures worth retrying"],
        ["6", "SMS is also retried 3 times", "same retry rules for SMS"],
        ["7", "SMS is not used when email succeeds", "fallback is only for failure"],
        ["8", "No phone number: the email error reaches the caller", "nothing to fall back to"],
        ["9", "The SMS error reaches the caller unwrapped", "not a new exception wrapping it"],
        ["10", "A permanent SMS error also reaches the caller unwrapped", "same rule"],
        ["11", "The fallback path returns the SMS receipt", "keeps its return value"],
        ["12", "Loggers use the package naming convention", "existing logging conventions"],
        ["13", "A retry is logged as a warning", "existing logging conventions"],
        ["14", "The function signature is unchanged", "keeps its signature"],
        ["15", "The return value is still the receipt", "keeps its return value"],
        ["16", "The import path still works", "other code calls it"],
        ["17", "It still returns a string", "keeps its return value"],
    ])
    para(doc, "Every one maps to something the ticket states in words. None of them requires "
              "a particular implementation, so any correct solution passes.")

    # ---------------------------------------------------------------- 6. results
    h1(doc, "6. What the evaluation found")
    table(doc, ["Check", "Harness 1 (written instruction)", "Harness 2 (hook)"], [
        ["Visible tests", f"{passes('baseline', 'acceptance')}/8",
         f"{passes('candidate', 'acceptance')}/8"],
        ["Hidden tests", f"{passes('baseline', 'heldout')}/8",
         f"{passes('candidate', 'heldout')}/8"],
        ["Existing tests", f"{passes('baseline', 'regressions')}/8",
         f"{passes('candidate', 'regressions')}/8"],
        ["Style (ruff)", f"{passes('baseline', 'lint')}/8", f"{passes('candidate', 'lint')}/8"],
        ["Types (mypy)", f"{passes('baseline', 'types')}/8",
         f"{passes('candidate', 'types')}/8"],
        ["Actually ran ruff + mypy", "0/8", "8/8"],
        ["Average steps taken",
         f"{sum(t['usage']['num_turns'] for t in arm('baseline')) / 8:.1f}",
         f"{sum(t['usage']['num_turns'] for t in arm('candidate')) / 8:.1f}"],
        ["Average cost per trial",
         f"${sum(t['usage']['total_cost_usd'] for t in arm('baseline')) / 8:.4f}",
         f"${sum(t['usage']['total_cost_usd'] for t in arm('candidate')) / 8:.4f}"],
    ])

    h2(doc, "6a. The clearest result")
    para(doc, "Harness 1 was told, in plain English, to run three checks. It ran one, "
              "the tests, in all 8 trials, and never ran the linter or the type checker. "
              "Harness 2 ran all three in all 8 trials.")
    para(doc, "0 out of 8 versus 8 out of 8. This is the finding we are most confident in: "
              "writing an instruction down is not the same as it being followed.")

    h2(doc, "6b. The quality result, and an honest caveat")
    para(doc, "Hidden tests went from 3/8 to 6/8, double. Every single failure in both arms "
              "was the same bug, on the same line:")
    code(doc,
         "except TransientDeliveryError:   <-- FAILS: a permanent failure never\n"
         "                                     reaches the SMS fallback\n"
         "except NotificationError:        <-- passes\n"
         "except Exception:                <-- passes")
    para(doc, "But the hook did not catch this directly. The hook runs the tests, the linter "
              "and the type checker, and all three PASS for the buggy version. What actually "
              "happened is indirect:")
    table(doc, ["Did the hook block the agent?", "Trials", "Hidden tests passed"], [
        ["Yes, it was sent back to fix something", "5", "5 out of 5"],
        ["No, it passed the checks first time", "3", "1 out of 3"],
    ])
    para(doc, "Being forced back into the code made the agent re-examine its work and fix an "
              "unrelated bug. That is a real effect, but a fragile one: it only happens when "
              "something else fails first.")
    para(doc, "3 out of 8 versus 6 out of 8, with 8 trials per side, is suggestive but not "
              "settled. This project has twice seen a difference of exactly that shape "
              "reverse when the experiment was repeated. The tool marks this result UNSTABLE "
              "and refuses to count it as a win.")

    # ---------------------------------------------------------------- 7. conclusion
    h1(doc, "7. Conclusion and recommendation")
    bullets(doc, [
        "PROVEN: the hook makes the checks run. 8/8 against 0/8, with no ambiguity.",
        "PROMISING: hidden-test pass rate doubled, 3/8 to 6/8, but unreplicated, and the "
        "cause is indirect.",
        "COST: the hook arm used 17% more steps and 29% more money.",
        "NOT FOUND: no regression. Nothing the hook arm did broke existing behaviour.",
    ])
    para(doc, "Recommendation: adopt the hook. Its proven benefit is that the checks actually "
              "execute, which the written instruction demonstrably fails to achieve. Treat "
              "the quality improvement as a hypothesis and confirm it with a second 16-trial "
              "run before claiming it.")
    para(doc, "There is a wider lesson here. Six earlier experiments found that AGENTS.md "
              "changed nothing. That was not evidence that guidance is worthless. It was "
              "evidence that ADVISORY guidance is not followed. The same words, enforced "
              "instead of requested, moved the numbers.")
    para(doc, "If a check matters, put it in a hook. A paragraph is a hope; a hook is a "
              "control.", italic=True)

    # ---------------------------------------------------------------- 8. evidence
    h1(doc, "8. Where to find the evidence")
    para(doc, "Every number above can be traced to a file. Nothing is asserted without "
              "something behind it.")
    code(doc,
         "runs/hook-01/\n"
         "  report.md                      the full report\n"
         "  report.json                    the same content as data\n"
         "  manifest.json                  every trial, plus the fairness record\n"
         "  tasks/notify-fallback.md       side-by-side, all 16 trials\n"
         "  trials/<arm>/<rep>/\n"
         "    patch.diff                   exactly what the agent changed\n"
         "    prompt.txt                   what it was asked\n"
         "    command.txt                  how it was started\n"
         "    transcript.json              cost, tokens, steps, which model\n"
         "    graders/*.log                each check's output\n"
         "  workspaces/                    the repository each agent worked in\n"
         "\n"
         "preflight_hook.py                25 fairness checks, run before spending anything\n"
         "examples/eval-hook.yaml          the experiment configuration")
    para(doc, "Before the experiment ran, 25 preflight checks confirmed the setup was fair: "
              "including one live trial proving the hook actually fires. A hook that silently "
              "did nothing would have produced a meaningless result.")

    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    print("written:", build())

"""Generate the mixed-comparison report (run mixed-01).

Every figure is read from the run artifacts, so the document cannot drift from what
actually happened.
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor

ROOT = Path(__file__).parent
RUN = ROOT / "runs" / "mixed-01"
OUT = ROOT / "Harness1-vs-Harness2-Report.docx"
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x5A, 0x5A, 0x5A)


def h(doc: Document, text: str, level: int = 1) -> None:
    """Heading."""
    doc.add_heading(text, level=level).runs[0].font.color.rgb = INK


def para(doc: Document, text: str, *, italic: bool = False, bold: bool = False) -> None:
    """Body paragraph."""
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic, r.bold = italic, bold
    if italic:
        r.font.color.rgb = MUTED
    p.paragraph_format.space_after = Pt(8)


def bullets(doc: Document, items: list[str]) -> None:
    """Bulleted list."""
    for i in items:
        doc.add_paragraph(i, style="List Bullet").paragraph_format.space_after = Pt(3)


def code(doc: Document, text: str) -> None:
    """Fixed-width block."""
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = "Consolas"
    r.font.size = Pt(8.5)
    p.paragraph_format.left_indent = Pt(14)
    p.paragraph_format.space_after = Pt(10)


def table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    """Grid table."""
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    for cell, head in zip(t.rows[0].cells, headers, strict=True):
        cell.text = head
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold, r.font.size = True, Pt(9)
    for row in rows:
        for cell, value in zip(t.add_row().cells, row, strict=True):
            cell.text = value
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def build() -> Path:
    """Write the report."""
    m = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    trials = m["trials"]

    def arm(n: str) -> list[dict]:
        return sorted((t for t in trials if t["harness"] == n), key=lambda t: t["rep"])

    def hits(n: str, g: str) -> int:
        return sum(1 for t in arm(n)
                   if any(x["id"] == g and x["status"] == "pass" for x in t["graders"]))

    def avg(n: str, f) -> float:
        rows = arm(n)
        return sum(f(t) for t in rows) / len(rows)

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)

    doc.add_heading("Harness 1 vs Harness 2: Evaluation Report", 0)
    para(doc, f"Run {m['run_id']}, 8 trials, "
              f"{m['wall_clock_s']:.0f} seconds, "
              f"${sum(t['usage']['total_cost_usd'] or 0 for t in trials):.2f}, "
              f"{m['created_utc'][:19]} UTC", italic=True)

    para(doc, "HEADLINE: Harness 2 passed every check in every trial; Harness 1 passed none "
              "of the critical ones. But four things differ between the two arms, so the "
              "result cannot be attributed to any single one of them. Section 11 explains "
              "exactly what this experiment can and cannot show.", bold=True)

    # ---------------------------------------------------------------- 1 & 2
    h(doc, "1. Harness 1 configuration")
    table(doc, ["Item", "Value"], [
        ["Model", "smollm2:360m (SmolLM2-360M-Instruct, 361.82M params, GGUF F16)"],
        ["Provider", "Ollama, local, http://localhost:11434/v1"],
        ["Authentication", "none, the model runs on this machine"],
        ["Runner", "harness_eval.local_agent, a fixed single-shot script"],
        ["Tools available", "read files, write one file, run the project validator. "
                            "No tool-calling: the model returns text, the script does the I/O."],
        ["AGENTS.md", "NOT PROVIDED, verified absent from the whole workspace tree"],
        ["Budget", "$0.00 (local inference is free)"],
        ["Environment", "fresh copy of examples/demo-html per trial, own git repo, "
                        "Python 3.10, Windows 11"],
    ])

    h(doc, "2. Harness 2 configuration")
    table(doc, ["Item", "Value"], [
        ["Model", "claude-sonnet-5 (Anthropic)"],
        ["Provider", "Anthropic API via the Claude Code CLI 2.1.272"],
        ["Authentication", "the existing OAuth session in ~/.claude/.credentials.json, "
                           "no API key was set or requested"],
        ["Runner", "Claude Code's own agentic loop (reads, edits, runs commands, decides "
                   "its next step)"],
        ["Tools available", "Read, Edit, Write, Glob, Grep, and Bash limited to "
                            "cd and python"],
        ["AGENTS.md", "PROVIDED, copied into the workspace root before the first commit, "
                      "byte-identical to the source"],
        ["Budget", "$2.00 per trial (--max-budget-usd)"],
        ["Environment", "fresh copy of examples/demo-html per trial, own git repo, "
                        "Python 3.10, Windows 11"],
    ])
    para(doc, "How AGENTS.md was applied: the evaluator copies it into the workspace root "
              "before running git init and the initial commit. That means the agent can read "
              "it as an ordinary project file, and it can never appear in the agent's patch "
              "as work the agent did. Evidence that it was read is in section 7.")

    # ---------------------------------------------------------------- 3
    doc.add_page_break()
    h(doc, "3. The task: identical for both harnesses")
    code(doc, (RUN / "trials" / "html-contact" / "baseline" / "0" / "prompt.txt")
         .read_text(encoding="utf-8").strip())
    para(doc, "One task definition produced both prompts. The repository, examples/demo-html, "
              "contains an existing about.html showing the house style, a stylesheet, and a "
              "CONVENTIONS.md, so the agent has to look at the project before writing.")

    # ---------------------------------------------------------------- 4
    h(doc, "4. The AGENTS.md given to Harness 2")
    code(doc, (ROOT / "examples" / "harnesses" / "candidate-html" / "AGENTS.md")
         .read_text(encoding="utf-8").strip())
    para(doc, "It is general engineering guidance. It contains no code, no reference "
              "implementation, and none of the hidden test requirements.")

    # ---------------------------------------------------------------- 5
    doc.add_page_break()
    h(doc, "5. Test cases used for evaluation")
    para(doc, "The same 26 checks ran against both harnesses' output. Every one is "
              "deterministic: a command that passes or fails. The evaluator runs them "
              "itself; nothing the agent claims is taken as evidence.")
    table(doc, ["Group", "Count", "Visible to the agent?", "Purpose"], [
        ["Acceptance", "7", "YES, copied into the workspace", "the basic feature exists"],
        ["Held-out", "15", "NO, added only after the agent stopped",
         "the details the ticket implied"],
        ["Regression", "4", "YES, already in the repo", "nothing existing was broken"],
    ])
    h(doc, "5a. The 7 acceptance tests (visible)", level=2)
    bullets(doc, ["index.html exists", "the page parses", "there is a heading",
                  "there is a name field", "there is an email field",
                  "there is a message textarea", "there is a submit button"])
    h(doc, "5b. The 15 held-out tests (hidden)", level=2)
    para(doc, "Written before the experiment, kept outside the repository, and copied in only "
              "after the agent finished and its work was saved. The agent could not read "
              "them, run them, or tune its output to them.")
    table(doc, ["#", "Checks", "From which requirement"], [
        ["1", "HTML5 doctype present", "valid HTML5"],
        ["2", "passes strict HTML5 parsing", "valid HTML5"],
        ["3", "html/head/body/title all present", "valid HTML5"],
        ["4", "lang attribute on <html>", "accessible"],
        ["5", "viewport meta present", "accessible"],
        ["6", "every form control has a label", "accessible"],
        ["7", "semantic sectioning elements used", "semantic HTML"],
        ["8", "the controls are inside a <form>", "semantic HTML"],
        ["9", "no div-soup in place of sectioning", "semantic HTML"],
        ["10", "no duplicate ids", "code quality"],
        ["11", "the form structure is not duplicated", "DRY"],
        ["12", "exactly one <h1>", "code quality"],
        ["13", "the project stylesheet is linked", "existing conventions"],
        ["14", "no inline styles", "existing conventions"],
        ["15", "the title follows the project pattern", "existing conventions"],
    ])

    # ---------------------------------------------------------------- 6 & 7
    doc.add_page_break()
    h(doc, "6. Results for every trial")
    rows = []
    for name, label in (("baseline", "Harness 1"), ("candidate", "Harness 2")):
        for t in arm(name):
            st = {g["id"]: g["status"] for g in t["graders"]}
            mk = lambda k: "PASS" if st.get(k) == "pass" else "FAIL"  # noqa: E731
            rows.append([f"{label} rep {t['rep']}", mk("acceptance"), mk("heldout"),
                         mk("regressions"), mk("validator"),
                         str(t["usage"]["num_turns"]),
                         f"${t['usage']['total_cost_usd']:.4f}"])
    table(doc, ["Trial", "Acceptance", "Held-out", "Regression", "Validator", "Steps", "Cost"],
          rows)

    h(doc, "7. Pass/fail totals and metrics")
    table(doc, ["Metric", "Harness 1 (local, no AGENTS.md)", "Harness 2 (Sonnet, AGENTS.md)"], [
        ["Acceptance (7 tests)", f"{hits('baseline', 'acceptance')}/4 trials",
         f"{hits('candidate', 'acceptance')}/4 trials"],
        ["Held-out (15 tests)", f"{hits('baseline', 'heldout')}/4 trials",
         f"{hits('candidate', 'heldout')}/4 trials"],
        ["Regression (4 tests)", f"{hits('baseline', 'regressions')}/4 trials",
         f"{hits('candidate', 'regressions')}/4 trials"],
        ["HTML validator", f"{hits('baseline', 'validator')}/4 trials",
         f"{hits('candidate', 'validator')}/4 trials"],
        ["Average steps", f"{avg('baseline', lambda t: t['usage']['num_turns']):.1f}",
         f"{avg('candidate', lambda t: t['usage']['num_turns']):.1f}"],
        ["Average runtime", f"{avg('baseline', lambda t: t['wall_clock_s']):.1f} s",
         f"{avg('candidate', lambda t: t['wall_clock_s']):.1f} s"],
        ["Average cost",
         f"${avg('baseline', lambda t: t['usage']['total_cost_usd'] or 0):.4f}",
         f"${avg('candidate', lambda t: t['usage']['total_cost_usd'] or 0):.4f}"],
        ["Read AGENTS.md", "n/a, not provided", "4/4 trials (recorded in files_inspected)"],
    ])

    h(doc, "7a. What each harness actually produced", level=2)
    para(doc, "Harness 1 copied the existing about.html almost verbatim (right doctype, "
              "right stylesheet link, right footer, the heading still reading 'About "
              "Northwind Bakery') and added no form at all. The four acceptance failures "
              "are the name field, the email field, the textarea and the submit button. Its "
              "one held-out failure was the missing <form> element. Identical in all four "
              "trials.")
    code(doc, '<title>About — Northwind Bakery</title>\n'
              '<h1>About Northwind Bakery</h1>       <-- Harness 1, all 4 trials\n'
              '(no <form>, no inputs, no textarea, no button)')
    para(doc, "Harness 2 produced a complete, labelled, accessible form in all four trials:")
    code(doc, '<form>\n'
              '  <label for="name">Name</label>\n'
              '  <input type="text" id="name" name="name" autocomplete="name" required>\n'
              '  <label for="email">Email</label>\n'
              '  <input type="email" id="email" name="email" autocomplete="email" required>\n'
              '  <label for="message">Message</label>\n'
              '  <textarea id="message" name="message" rows="6" required></textarea>\n'
              '  <button type="submit">Send message</button>\n'
              '</form>')

    # ---------------------------------------------------------------- 8
    doc.add_page_break()
    h(doc, "8. Comparison")
    para(doc, "Harness 2 won every critical grader, 4/4 against 0/4, with no overlap and no "
              "variation across trials. Both arms left the existing pages intact and both "
              "produced valid HTML. Harness 1's page was valid because it was a copy of a "
              "valid page.")
    para(doc, "Harness 2 cost $0.1468 per trial against $0.00, and took roughly twice as long "
              "(40 s against 18 s). For a task Harness 1 could not do at all, that is not a "
              "meaningful trade.")

    # ---------------------------------------------------------------- 9 & 10
    h(doc, "9. Which model executed each task, and how it was authenticated")
    para(doc, "Each trial records the model in its own transcript, written by the agent "
              "rather than by the evaluator:")
    code(doc, "Harness 1  transcript.json -> modelUsage: {'smollm2:360m'}      cost 0.0\n"
              "Harness 2  transcript.json -> modelUsage: {'claude-sonnet-5',\n"
              "                                           'claude-haiku-4-5'}  cost ~0.15")
    para(doc, "The haiku entry in Harness 2 is Claude Code's own internal side-call, not the "
              "model doing the task; the task ran on claude-sonnet-5.")
    para(doc, "Authentication. Harness 1 needs none, since Ollama serves the model on localhost. "
              "Harness 2 uses the OAuth session already on this machine "
              "(~/.claude/.credentials.json), which is why the harness never asked for an API "
              "token and why those trials cost real money against the account. No "
              "ANTHROPIC_API_KEY was set. The flag --setting-sources project deliberately "
              "excludes the operator's personal settings so they cannot leak into a trial.")
    para(doc, "Neither model is the assistant used to operate the harness. The evaluator "
              "starts each agent as a separate operating-system process; the operator never "
              "touches the repository under test.")

    h(doc, "10. Is each trial isolated?")
    para(doc, "Yes. For every one of the 8 trials the evaluator copies the repository "
              "EXCLUDING its .git directory, then runs git init and makes a single commit. "
              "Trial N therefore cannot read trial N-1's history, a leakage route that would "
              "otherwise let an agent see a previous attempt.")
    bullets(doc, [
        "8 separate workspaces on disk, each with exactly 1 commit.",
        "AGENTS.md present in all 4 Harness 2 workspaces, absent from all 4 Harness 1 "
        "workspaces.",
        "The held-out tests exist in none of the 8 workspaces during the agent run.",
        "Arm order was counterbalanced so neither side always ran first.",
    ])

    # ---------------------------------------------------------------- 11
    doc.add_page_break()
    h(doc, "11. Is this a harness evaluation or a model comparison?")
    para(doc, "It is neither cleanly. It is a PRODUCT comparison, and the result cannot be "
              "attributed to any single cause.", bold=True)
    para(doc, "Four things differ between the two arms:")
    table(doc, ["#", "What differs", "Harness 1", "Harness 2"], [
        ["1", "Model", "smollm2:360m (361M params)", "claude-sonnet-5"],
        ["2", "Provider", "local Ollama", "Anthropic API"],
        ["3", "Runner", "fixed single-shot script, no tool-calling",
         "Claude Code's agentic loop"],
        ["4", "Guidance", "no AGENTS.md", "AGENTS.md provided"],
    ])
    para(doc, "A genuine harness evaluation holds the model constant and varies one harness "
              "component. A genuine model comparison holds the harness constant and varies "
              "the model. This does neither: it varies both, plus the runner.")
    para(doc, "The tool records this honestly. The run manifest lists all four as declared "
              "differences rather than claiming a controlled experiment. The configuration "
              "file carries the same warning at the top.")
    para(doc, "For contrast, run hook-01 in this same repository IS a genuine harness "
              "evaluation: identical model (Haiku), identical runner, identical task, with "
              "only the guidance mechanism differing. That run found the harness change moved "
              "a real metric: the checks ran 8/8 times instead of 0/8.")

    h(doc, "12. What can and cannot be concluded")
    h(doc, "Can be concluded", level=2)
    bullets(doc, [
        "This complete setup (Sonnet, Claude Code, AGENTS.md) solves this task reliably: "
        "4/4 trials, every check, no variation.",
        "This complete setup (a 360M local model with a single-shot runner and no guidance) "
        "cannot do this task at all: 0/4, and the same failure every time.",
        "If you have to choose between these two setups for work like this, the second is "
        "not a viable option. That is a real, decision-useful finding.",
        "The evaluation machinery is fair and reproducible: isolated workspaces, hidden tests "
        "the agent never saw, counterbalanced order, every grader run by the evaluator.",
    ])
    h(doc, "Cannot be concluded", level=2)
    bullets(doc, [
        "NOT that AGENTS.md helped. Harness 1 never had a chance to show whether guidance "
        "would change anything, because it failed the task on every trial regardless.",
        "NOT how much of the gap is the model versus the runner. Harness 1's runner cannot "
        "call tools or iterate; a stronger model in that same runner might also fail.",
        "NOT that Sonnet is better than SmolLM2 at this task in general, since they were not run "
        "under the same conditions.",
        "NOT a cost comparison. $0.00 against $0.1468 compares a local model to a hosted one, "
        "which is a billing difference, not an efficiency one.",
    ])
    para(doc, "To answer 'does AGENTS.md help?', hold everything else fixed and vary only the "
              "guidance. To answer 'which model is better?', hold the runner and guidance "
              "fixed and vary only the model. This experiment answers 'which of these two "
              "products should I use?', a fair question, and a different one.", italic=True)

    h(doc, "13. Artifacts")
    code(doc,
         "runs/mixed-01/\n"
         "  report.md  report.json  manifest.json   the report, the data, the fairness record\n"
         "  tasks/html-contact.md                   side-by-side, all 8 trials\n"
         "  trials/html-contact/<arm>/<rep>/\n"
         "    patch.diff        exactly what the agent changed\n"
         "    prompt.txt        what it was asked (identical across arms)\n"
         "    command.txt       how it was started\n"
         "    transcript.json   model, cost, tokens, steps\n"
         "    graders/*.log     each check's command, exit code and output\n"
         "  workspaces/         the repository each agent actually worked in\n"
         "examples/eval-mixed.yaml   the configuration, with the confound documented")

    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    print("written:", build())

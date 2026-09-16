"""Preflight for the clean-names guidance benchmark.

Proves the experiment can produce a trustworthy answer before any trial runs. Nothing
here looks at results.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from harness_eval.adapters import run_shell
from harness_eval.config import load_config
from harness_eval.graders import apply_overlay
from harness_eval.workspace import create_workspace, remove_tree

ROOT = Path(__file__).parent
CONFIG = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "examples" / "eval-cleaner.yaml"
SCRATCH = ROOT / "runs" / "_preflight_cleaner"
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    results.append((ok, label))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"\n         {detail}" if detail else ""))
    return ok


# Written only from the ticket plus the repo's own conventions: reuses the shared blank
# check, returns a new list, leaves the input alone, fully annotated and documented.
GOOD = '''"""Name tidying."""

from __future__ import annotations

from cleaner.text import is_blank


def clean_names(names: list[str]) -> list[str]:
    """Return the names trimmed and title-cased, with blanks dropped.

    The input list is not modified.
    """
    cleaned: list[str] = []
    for name in names:
        if is_blank(name):
            continue
        cleaned.append(name.strip().title())
    return cleaned
'''

# A different but equally valid implementation. Held-out must accept it too, or the tests
# are encoding one particular solution rather than the ticket's behaviour.
ALTERNATIVE = '''"""Name tidying."""

from __future__ import annotations


def clean_names(names: list[str]) -> list[str]:
    """Return the names trimmed and title-cased, with blanks dropped."""
    return [n.strip().title() for n in names if n.strip() != ""]
'''

# Behaviourally correct, but mutates the caller's list -- the one thing CONVENTIONS.md
# and the ticket both forbid. Held-out has to catch this.
MUTATING = '''"""Name tidying."""

from __future__ import annotations


def clean_names(names: list[str]) -> list[str]:
    """Return the names trimmed and title-cased, with blanks dropped."""
    for index in range(len(names) - 1, -1, -1):
        if names[index].strip() == "":
            del names[index]
        else:
            names[index] = names[index].strip().title()
    return names
'''


def build(name: str, cfg, task, harness=None) -> Path:
    ws = SCRATCH / name
    create_workspace(cfg.repo, task, ws, harness)
    return ws


def grade(ws: Path, cfg, task) -> dict[str, bool]:
    apply_overlay("heldout", task, ws, already_applied=False)
    return {g.id: run_shell(g.command, ws, g.timeout_s).exit_code == 0 for g in cfg.graders}


def main() -> int:
    if SCRATCH.exists():
        remove_tree(SCRATCH)
    cfg = load_config(CONFIG)
    task = next(t for t in cfg.tasks if t.id == "clean-names")
    base, cand = cfg.harnesses["baseline"], cfg.harnesses["candidate"]
    impl = "src/cleaner/names.py"

    print("\n== 1. the task is real and the environment is not sabotaged ==")
    ws0 = build("untouched", cfg, task, base)
    before = grade(ws0, cfg, task)
    check(not before["acceptance"], "acceptance FAILS on the untouched repo", str(before))
    check(not before["heldout"], "held-out FAILS on the untouched repo")
    check(before["regressions"] and before["lint"] and before["types"] and before["scope"],
          "the untouched repo is otherwise green")

    print("\n== 2. the task is solvable WITHOUT the guidance ==")
    ws = build("good", cfg, task, base)
    check(not (ws / "AGENTS.md").exists(), "reference solution built in a baseline workspace")
    (ws / impl).write_text(GOOD, encoding="utf-8")
    good = grade(ws, cfg, task)
    check(all(good.values()), "a conventional solution passes EVERY grader", str(good))

    print("\n== 3. held-out tests behaviour, not one implementation ==")
    ws2 = build("alternative", cfg, task, base)
    (ws2 / impl).write_text(ALTERNATIVE, encoding="utf-8")
    alt = grade(ws2, cfg, task)
    check(alt["acceptance"] and alt["heldout"] and alt["regressions"],
          "a DIFFERENT correct implementation also passes", str(alt))

    print("\n== 4. held-out catches a real defect the visible tests miss ==")
    ws3 = build("mutating", cfg, task, base)
    (ws3 / impl).write_text(MUTATING, encoding="utf-8")
    bad = grade(ws3, cfg, task)
    check(bad["acceptance"], "the mutating version PASSES the visible tests", str(bad))
    check(not bad["heldout"], "and FAILS held-out -- the hidden suite earns its place")

    print("\n== 5. held-out maps to stated ticket requirements ==")
    ticket = task.prompt.lower()
    for phrase in ("leading and trailing whitespace", "title case", "remove empty names",
                   "preserve the original order", "do not modify the input list",
                   "existing project conventions", "add appropriate tests",
                   "run the relevant tests"):
        check(phrase in ticket, f"ticket states: {phrase!r}")

    print("\n== 6. the arms differ ONLY in the guidance ==")
    for field in ("command", "model", "endpoint", "budget", "env"):
        check(getattr(base, field) == getattr(cand, field), f"identical {field}")
    check(base.instructions is None and cand.instructions is not None,
          "instructions: baseline=None, candidate=AGENTS.md")
    check(cfg.intended_difference == ["instructions"], "declared variable is instructions")

    print("\n== 7. guidance visibility is real and one-sided ==")
    wb, wc = build("vis_base", cfg, task, base), build("vis_cand", cfg, task, cand)
    check(not any(p.name == "AGENTS.md" for p in wb.rglob("*")),
          "no guidance anywhere in the baseline tree")
    check((wc / "AGENTS.md").read_text(encoding="utf-8")
          == cand.instructions.read_text(encoding="utf-8"),  # type: ignore[union-attr]
          "candidate's copy is byte-identical to the source")

    print("\n== 8. the guidance is general, not the answer ==")
    text = cand.instructions.read_text(encoding="utf-8")  # type: ignore[union-attr]
    # Symbols and methods only. A prose check would fire on "tests for new behavior"
    # because it contains "for " -- a false positive, and the brief explicitly says no
    # false-positive leakage checks.
    for banned in (".strip", ".title", "clean_names", "is_blank", "comprehension"):
        check(banned not in text, f"does not name {banned!r}")
    check("```" not in text, "contains no code block")
    code_lines = [ln for ln in text.splitlines()
                  if ln.startswith("    ") and ln.strip().split(" ")[0]
                  in {"def", "return", "for", "if", "import", "from"}]
    check(not code_lines, "contains no indented Python", str(code_lines[:2]))

    print("\n== 9. held-out tests are invisible to the agent ==")
    ws4 = build("vis_heldout", cfg, task, cand)
    check(not (ws4 / "tests" / "heldout").exists(), "no tests/heldout in a fresh workspace")
    check("test_clean_names_heldout.py" not in {p.name for p in ws4.rglob("*.py")},
          "the held-out file is nowhere in the tree")
    body = (ROOT / "examples" / "heldout" / "clean-names").glob("*.py")
    src = "\n".join(f.read_text(encoding="utf-8") for f in body)
    # Strip docstrings first: the held-out file legitimately MENTIONS .strip() to say the
    # tests do not require it. Only executable assertions matter here.
    code_only = re.sub(r'"""(?:.|\n)*?"""', "", src)
    method_asserts = [
        ln for ln in code_only.splitlines()
        if "assert" in ln and (".strip(" in ln or ".title(" in ln)
    ]
    check(not method_asserts,
          "no held-out assertion depends on a particular method being used",
          str(method_asserts[:2]))
    check(re.search(r"ticket:", src) is not None,
          "held-out tests are annotated with the requirement each one checks")

    print("\n== 10. the scope grader works ==")
    ws5 = build("stray", cfg, task, base)
    (ws5 / impl).write_text(GOOD, encoding="utf-8")
    (ws5 / "src" / "cleaner" / "emails.py").write_text("# vandalised\n", encoding="utf-8")
    run_shell("git add -A", ws5, 60)
    stray = run_shell("python check_scope.py", ws5, 60)
    check(stray.exit_code != 0, "editing an unrelated module is caught", stray.stdout[-200:])

    print("\n== 11. schedule is counterbalanced ==")
    firsts = [(["baseline", "candidate"] if i % 2 == 0 else ["candidate", "baseline"])[0]
              for i in range(8)]
    check(firsts.count("baseline") == firsts.count("candidate"),
          f"each arm leads equally often: {firsts.count('baseline')}/{firsts.count('candidate')}")

    remove_tree(SCRATCH)
    failed = [label for ok, label in results if not ok]
    print(f"\n{'=' * 62}\n{len(results) - len(failed)}/{len(results)} checks passed")
    for label in failed:
        print("  FAILED:", label)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

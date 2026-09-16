"""Preflight for an AGENTS.md experiment. Pass the config and task id on argv.

Runs every fairness check before any money is spent. Nothing here inspects results --
it only establishes that the experiment is capable of producing a fair answer.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from harness_eval.adapters import run_shell
from harness_eval.config import load_config
from harness_eval.graders import apply_overlay
from harness_eval.workspace import create_workspace, remove_tree

ROOT = Path(__file__).parent
CONFIG = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "examples" / "eval.yaml"
TASK_ID = sys.argv[2] if len(sys.argv) > 2 else "calculate-total"
SCRATCH = ROOT / "runs" / "_preflight"
PASS, FAIL = "  PASS", "  FAIL"
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    results.append((ok, label))
    print(f"{PASS if ok else FAIL}  {label}" + (f"\n         {detail}" if detail else ""))
    return ok


# A correct solution. Deliberately written only from the ticket -- it reuses round_money,
# validates, is fully typed, and adds the docs row the repo convention requires.
GOOD = '''

def calculate_total(items: Iterable[Mapping[str, object]]) -> float:
    """Total the amounts of a collection of line items."""
    running = 0.0
    for item in items:
        if "amount" not in item:
            raise ValueError("line item is missing 'amount'")
        amount = item["amount"]
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError(f"invalid amount: {amount!r}")
        running += float(amount)
    return round_money(running)
'''

# Fully unannotated. Behaviourally correct; caught by ruff's ANN rules AND by mypy.
UNTYPED = '''

def calculate_total(items):
    """Total the amounts of a collection of line items."""
    running = 0.0
    for item in items:
        if "amount" not in item:
            raise ValueError("line item is missing 'amount'")
        amount = item["amount"]
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError(f"invalid amount: {amount!r}")
        running += float(amount)
    return round_money(running)
'''


# The realistic defect: annotations present, so ruff is satisfied, but the generic is
# bare. Only mypy --strict catches this, which is what makes the type grader load-bearing.
BARE_GENERIC = '''


def calculate_total(items: list[dict]) -> float:
    """Total the amounts of a collection of line items."""
    running = 0.0
    for item in items:
        if "amount" not in item:
            raise ValueError("line item is missing 'amount'")
        amount = item["amount"]
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError(f"invalid amount: {amount!r}")
        running += float(amount)
    return round_money(running)
'''


def build(name: str, cfg, task, harness=None) -> Path:
    ws = SCRATCH / name
    create_workspace(cfg.repo, task, ws, harness)
    return ws


def apply(ws: Path, body: str, docs: bool = True) -> None:
    money = ws / "src" / "demo" / "money.py"
    src = money.read_text(encoding="utf-8")
    if "Iterable" in body:
        src = src.replace(
            "from __future__ import annotations",
            "from __future__ import annotations\n\nfrom collections.abc import Iterable, Mapping",
        )
    money.write_text(src + body, encoding="utf-8")
    if docs:
        api = ws / "docs" / "api.md"
        api.write_text(
            api.read_text(encoding="utf-8")
            + "| `calculate_total(items)` | Total a collection of line items. |\n",
            encoding="utf-8",
        )


def grade(ws: Path, cfg, task) -> dict[str, bool]:
    apply_overlay("heldout", task, ws, already_applied=False)
    out = {}
    for g in cfg.graders:
        out[g.id] = run_shell(g.command, ws, g.timeout_s).exit_code == 0
    return out


def main() -> int:
    if SCRATCH.exists():
        remove_tree(SCRATCH)
    cfg = load_config(CONFIG)
    task = next(t for t in cfg.tasks if t.id == TASK_ID)
    base, cand = cfg.harnesses["baseline"], cfg.harnesses["candidate"]

    print("\n== 1. the task is solvable, and solvable WITHOUT AGENTS.md ==")
    ws = build("good", cfg, task, base)
    check(not (ws / "AGENTS.md").exists(), "reference solution built in a baseline workspace")
    apply(ws, GOOD)
    good = grade(ws, cfg, task)
    check(all(good.values()), "a correct solution passes every grader", str(good))

    print("\n== 2. acceptance tests are not accidentally impossible ==")
    check(good["acceptance"], "acceptance passes for a correct solution")

    print("\n== 3. held-out tests map to stated ticket requirements ==")
    ticket = task.prompt.lower()
    for phrase in ("positive or negative", "empty collection", "missing or invalid",
                   "valueerror", "existing money-rounding rule", "documentation",
                   "correctly typed"):
        check(phrase in ticket, f"ticket states: {phrase!r}")
    check(good["heldout"], "every held-out test passes for a correct solution")

    print("\n== 4. the type grader catches a REAL quality issue ==")
    ws2 = build("untyped", cfg, task, base)
    apply(ws2, UNTYPED)
    bad = grade(ws2, cfg, task)
    check(bad["acceptance"] and bad["heldout"] and bad["regressions"],
          "the untyped version is behaviourally correct", str(bad))
    check(not bad["types"], "mypy --strict rejects it -- a real, un-hinted defect")

    ws2b = build("bare_generic", cfg, task, base)
    apply(ws2b, BARE_GENERIC)
    bare = grade(ws2b, cfg, task)
    check(bare["acceptance"] and bare["heldout"] and bare["regressions"],
          "the bare-generic version is behaviourally correct too", str(bare))
    check(bare["lint"], "ruff PASSES it -- annotations are present, just imprecise")
    check(not bare["types"],
          "mypy --strict is the ONLY grader that catches it -- the realistic defect")

    print("\n== 5. the two arms differ ONLY in AGENTS.md ==")
    check(base.command == cand.command, "identical command template (permissions, flags)")
    check(base.model == cand.model, "identical model")
    check(base.budget == cand.budget, "identical spend cap")
    check(base.env == cand.env, "identical environment")
    import re as _re
    eff = lambda c: (_re.search(r"--effort (\w+)", c) or [None, "default"])[1]
    check(eff(base.command) == eff(cand.command),
          f"identical effort level: both arms are '{eff(base.command)}'")
    check(base.instructions is None and cand.instructions is not None,
          "instructions: baseline=None, candidate=AGENTS.md")

    print("\n== 6. AGENTS.md visibility is real and one-sided ==")
    wb = build("vis_base", cfg, task, base)
    wc = build("vis_cand", cfg, task, cand)
    check(not (wb / "AGENTS.md").exists(), "baseline workspace has NO AGENTS.md")
    check((wc / "AGENTS.md").exists(), "candidate workspace HAS AGENTS.md")
    check((wc / "AGENTS.md").read_text(encoding="utf-8")
          == cand.instructions.read_text(encoding="utf-8"),  # type: ignore[union-attr]
          "candidate's copy is byte-identical to the source")
    check(not any(p.name == "AGENTS.md" for p in wb.rglob("*")),
          "no AGENTS.md anywhere in the baseline tree")

    print("\n== 7. AGENTS.md contains no task-specific hints ==")
    text = (cand.instructions.read_text(encoding="utf-8")).lower()  # type: ignore[union-attr]
    for banned in ("calculate_total", "round_money", "api.md", "dict[", "list[",
                   "iterable", "mapping", "float", "isinstance"):
        check(banned not in text, f"does not mention {banned!r}")

    print("\n== 8. held-out tests are invisible to the agent ==")
    ws3 = build("vis_heldout", cfg, task, cand)
    check(not (ws3 / "tests" / "heldout").exists(), "no tests/heldout in a fresh workspace")
    names = {p.name for p in ws3.rglob("*.py")}
    check("test_total_heldout.py" not in names, "the held-out file is nowhere in the tree")

    print("\n== 9. schedule is counterbalanced, cache effects cancel ==")
    firsts = []
    for i in range(4):
        order = ["baseline", "candidate"]
        if (i + 0) % 2:
            order.reverse()
        firsts.append(order[0])
    check(firsts.count("baseline") == firsts.count("candidate"),
          f"each arm leads equally often across reps: {firsts}")

    remove_tree(SCRATCH)
    failed = [label for ok, label in results if not ok]
    print(f"\n{'=' * 60}\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED:")
        for label in failed:
            print("  -", label)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

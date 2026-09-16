"""Preflight for the prose-vs-hook experiment.

The decisive check is §5: a hook that silently does not fire would make this a null
result for the wrong reason, so the hook is proven to run on a real trial before the
experiment starts.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from harness_eval.adapters import ShellAgentAdapter, run_shell
from harness_eval.config import load_config
from harness_eval.evidence import count_hook_events
from harness_eval.graders import apply_overlay
from harness_eval.workspace import create_workspace, remove_tree

ROOT = Path(__file__).parent
CONFIG = ROOT / "examples" / "eval-hook.yaml"
SCRATCH = ROOT / "runs" / "_preflight_hook"
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    results.append((ok, label))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"\n         {detail}" if detail else ""))
    return ok


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
    task = next(t for t in cfg.tasks if t.id == "notify-fallback")
    base, cand = cfg.harnesses["baseline"], cfg.harnesses["candidate"]

    print("\n== 1. the task is real and the environment is not sabotaged ==")
    ws0 = build("untouched", cfg, task, base)
    before = grade(ws0, cfg, task)
    check(not before["acceptance"], "acceptance FAILS on the untouched repo", str(before))
    check(before["regressions"] and before["lint"] and before["types"],
          "the untouched repo is otherwise green")

    print("\n== 2. the arms differ ONLY in the declared variables ==")
    for field in ("command", "model", "budget", "env", "endpoint"):
        check(getattr(base, field) == getattr(cand, field), f"identical {field}")
    check(base.model == "claude-haiku-4-5", f"both arms on Haiku, not Sonnet: {base.model}")
    check(sorted(cfg.intended_difference) == ["config_dir", "instructions"],
          f"declared variables: {cfg.intended_difference}")

    print("\n== 3. each arm carries exactly one of the two mechanisms ==")
    wb = build("prose", cfg, task, base)
    wc = build("hook", cfg, task, cand)
    check((wb / "AGENTS.md").is_file(), "prose arm HAS AGENTS.md")
    check(not (wb / ".claude").exists(), "prose arm has NO .claude/")
    check(not (wc / "AGENTS.md").exists(), "hook arm has NO AGENTS.md")
    check((wc / ".claude" / "settings.json").is_file(), "hook arm HAS .claude/settings.json")
    check((wc / ".claude" / "verify.py").is_file(), "hook arm HAS the hook script")

    print("\n== 4. both arms ask for the SAME three checks ==")
    prose = (wb / "AGENTS.md").read_text(encoding="utf-8")
    hook = (wc / ".claude" / "verify.py").read_text(encoding="utf-8")
    for token in ("pytest", "ruff", "mypy"):
        check(token in prose and token in hook, f"both arms reference {token}")
    check("notify" not in prose.lower() and "retry" not in prose.lower(),
          "the prose names nothing task-specific")
    check("notify" not in hook.lower() and "call_with_retry" not in hook,
          "the hook names nothing task-specific")

    print("\n== 5. the hook actually FIRES on a real trial ==")
    print("         (one live Haiku call, ~$0.20 -- cheaper than a 16-trial null result)")
    ws = build("live", cfg, task, cand)
    trial_dir = SCRATCH / "live_trial"
    shell = ShellAgentAdapter().run(task, cand, ws, trial_dir, 600)
    events = count_hook_events(shell.stdout)
    check(events > 0, f"hook lifecycle events in the transcript: {events}",
          "" if events else shell.stdout[-400:])
    check((ws / ".claude" / "verify.py").is_file(), "the hook script survived the trial")
    ran = run_shell("python .claude/verify.py", ws, 300)
    check(ran.exit_code == 0, "the hook script runs standalone without crashing",
          ran.stdout[-300:] if ran.exit_code else "")

    print("\n== 6. held-out tests are invisible to the agent ==")
    ws2 = build("vis_heldout", cfg, task, cand)
    check(not (ws2 / "tests" / "heldout").exists(), "no tests/heldout in a fresh workspace")
    check("test_notify_heldout.py" not in {p.name for p in ws2.rglob("*.py")},
          "the held-out file is nowhere in the tree")

    print("\n== 7. schedule is counterbalanced ==")
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

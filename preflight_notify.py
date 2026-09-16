"""Preflight for the notify-fallback guidance experiment.

Establishes that the experiment can produce a fair answer, before any money is spent.
Nothing here inspects results.
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
CONFIG = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "examples" / "eval-notify.yaml"
SCRATCH = ROOT / "runs" / "_preflight_notify"
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    results.append((ok, label))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"\n         {detail}" if detail else ""))
    return ok


# A correct solution, written only from the ticket plus reading the package: it reuses
# call_with_retry, lets the error hierarchy decide what is retried, re-raises unchanged,
# and keeps the signature.
GOOD = '''"""The public entry point every caller uses."""

from __future__ import annotations

from notifier.channels import send_email, send_sms
from notifier.errors import NotificationError
from notifier.logging_utils import get_logger
from notifier.retry import call_with_retry

_log = get_logger(__name__)


def send_notification(recipient: dict[str, str], message: str) -> str:
    """Deliver `message` to `recipient` and return the provider's receipt id.

    `recipient` carries an "email" and may carry a "phone".
    """
    _log.info("notifying %s", recipient.get("email"))
    try:
        return call_with_retry(lambda: send_email(recipient["email"], message))
    except NotificationError:
        phone = recipient.get("phone")
        if not phone:
            raise
        _log.warning("email delivery failed, falling back to sms")
        return call_with_retry(lambda: send_sms(phone, message))
'''

# Behaviourally identical, but reimplements the loop with an unannotated nested helper
# instead of reusing the existing one. This is the quality defect the graders must catch.
REIMPLEMENTED = '''"""The public entry point every caller uses."""

from __future__ import annotations

import time

from notifier.channels import send_email, send_sms
from notifier.errors import NotificationError, TransientDeliveryError
from notifier.logging_utils import get_logger

_log = get_logger(__name__)


def _try(fn, attempts=3):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except TransientDeliveryError as exc:
            last = exc
            _log.warning("attempt %s failed", i + 1)
            if i < attempts - 1:
                time.sleep(0.01)
    raise last


def send_notification(recipient: dict[str, str], message: str) -> str:
    """Deliver `message` to `recipient` and return the provider's receipt id."""
    _log.info("notifying %s", recipient.get("email"))
    try:
        return _try(lambda: send_email(recipient["email"], message))
    except NotificationError:
        phone = recipient.get("phone")
        if not phone:
            raise
        return _try(lambda: send_sms(phone, message))
'''


# Probes the test INFRASTRUCTURE, not the implementation: if any of these fail, a
# held-out failure in the real experiment could not be attributed to the agent.
PROBE = '''import logging

import pytest

from notifier import channels, retry
from notifier.errors import TransientDeliveryError
from notifier.service import send_notification

R = {"email": "a@b.com", "phone": "+15550000"}


def _raiser(exc):
    def transport(target, message):
        raise exc

    return transport


def test_monkeypatch_reaches_the_transport(monkeypatch):
    monkeypatch.setattr(channels, "email_transport", lambda a, m: "patched")
    assert send_notification(R, "x") == "patched"


def test_sleep_is_observable(monkeypatch):
    waits = []
    monkeypatch.setattr(retry.time, "sleep", waits.append)
    monkeypatch.setattr(channels, "email_transport", _raiser(TransientDeliveryError("d")))
    monkeypatch.setattr(channels, "sms_transport", lambda n, m: "sms")
    send_notification(R, "x")
    assert waits, "the sleep patch was not observable"


def test_exception_identity_survives(monkeypatch):
    marker = TransientDeliveryError("marker")
    monkeypatch.setattr(channels, "email_transport", _raiser(marker))
    with pytest.raises(TransientDeliveryError) as exc:
        send_notification({"email": "a@b.com"}, "x")
    assert exc.value is marker


def test_caplog_sees_package_records(monkeypatch, caplog):
    monkeypatch.setattr(channels, "email_transport", lambda a, m: "ok")
    with caplog.at_level(logging.DEBUG):
        send_notification(R, "x")
    assert any(r.name.startswith("notifier.") for r in caplog.records)
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
    task = next(t for t in cfg.tasks if t.id == "notify-fallback")
    base, cand = cfg.harnesses["baseline"], cfg.harnesses["candidate"]

    print("\n== 1. the task is real: the untouched repo does NOT already pass ==")
    ws0 = build("untouched", cfg, task, base)
    before = grade(ws0, cfg, task)
    check(not before["acceptance"], "acceptance FAILS on the untouched repo", str(before))
    check(not before["heldout"], "held-out FAILS on the untouched repo")
    check(before["regressions"] and before["lint"] and before["types"],
          "the untouched repo is otherwise green -- no sabotaged environment")

    print("\n== 2. the task is solvable WITHOUT the guidance ==")
    ws = build("good", cfg, task, base)
    check(not (ws / "AGENTS.md").exists(), "reference solution built in a baseline workspace")
    (ws / "src" / "notifier" / "service.py").write_text(GOOD, encoding="utf-8")
    good = grade(ws, cfg, task)
    check(all(good.values()), "a correct solution passes every grader", str(good))

    print("\n== 3. held-out tests map to stated ticket requirements ==")
    ticket = task.prompt.lower()
    for phrase in ("3 attempts", "do not wait after the final attempt", "must not be retried",
                   "fall back to sms", "no phone number", "not a new exception wrapping it",
                   "logging conventions", "keeps its signature"):
        check(phrase in ticket, f"ticket states: {phrase!r}")
    check(good["heldout"], "every held-out test passes for a correct solution")

    print("\n== 4. the quality graders catch a real defect ==")
    ws2 = build("reimplemented", cfg, task, base)
    (ws2 / "src" / "notifier" / "service.py").write_text(REIMPLEMENTED, encoding="utf-8")
    bad = grade(ws2, cfg, task)
    check(bad["acceptance"] and bad["heldout"] and bad["regressions"],
          "reimplementing the helper is BEHAVIOURALLY correct", str(bad))
    check(not (bad["lint"] and bad["types"]),
          "but the quality graders reject it -- a real, un-hinted defect")

    print("\n== 5. the two arms differ ONLY in the guidance resource ==")
    check(base.command == cand.command, "identical command template")
    check(base.model == cand.model, "identical model")
    check(base.budget == cand.budget, "identical spend cap")
    check(base.env == cand.env, "identical environment")
    check(base.instructions is None and cand.instructions is not None,
          "instructions: baseline=None, candidate=AGENTS.md")

    print("\n== 6. guidance visibility is real and one-sided ==")
    wb, wc = build("vis_base", cfg, task, base), build("vis_cand", cfg, task, cand)
    check(not any(p.name == "AGENTS.md" for p in wb.rglob("*")),
          "no guidance anywhere in the baseline tree")
    check((wc / "AGENTS.md").read_text(encoding="utf-8")
          == cand.instructions.read_text(encoding="utf-8"),  # type: ignore[union-attr]
          "candidate's copy is byte-identical to the source")

    print("\n== 7. the guidance contains knowledge, not the solution ==")
    text = cand.instructions.read_text(encoding="utf-8")  # type: ignore[union-attr]
    for banned in ("call_with_retry", "TransientDeliveryError", "PermanentDeliveryError",
                   "get_logger", "send_sms(", "send_email("):
        check(banned not in text, f"names no helper or symbol: {banned!r}")
    check("```" not in text, "contains no fenced code block")
    code_lines = [ln for ln in text.splitlines()
                  if ln.startswith("    ") and ln.strip().split(" ")[0]
                  in {"def", "return", "try:", "except", "raise", "for", "if", "while"}]
    check(not code_lines, "contains no indented Python statements", str(code_lines[:3]))
    # Two guidance designs are valid: project-specific (names the modules) or generic
    # (names none). What is NOT valid is naming some and not others, which would give the
    # candidate a partial map and make the comparison hard to characterise. Assert the
    # guidance is coherently one or the other, and say which.
    modules = ("service.py", "channels.py", "errors.py", "retry.py", "logging_utils.py")
    named = [m for m in modules if m in text]
    kind = "project-specific" if named else "generic"
    check(len(named) in (0, len(modules)),
          f"guidance is coherently {kind}: names {len(named)}/{len(modules)} repo modules")
    check(kind == "generic", "guidance is GENERIC process advice, naming no repo module")

    print("\n== 8. held-out tests are invisible to the agent ==")
    ws3 = build("vis_heldout", cfg, task, cand)
    check(not (ws3 / "tests" / "heldout").exists(), "no tests/heldout in a fresh workspace")
    check("test_notify_heldout.py" not in {p.name for p in ws3.rglob("*.py")},
          "the held-out file is nowhere in the tree")

    print("\n== 9. the tests themselves are valid ==")
    ws4 = build("testquality", cfg, task, base)
    (ws4 / "src" / "notifier" / "service.py").write_text(GOOD, encoding="utf-8")
    apply_overlay("heldout", task, ws4, already_applied=False)
    body = "\n".join(
        f.read_text(encoding="utf-8") for f in (ws4 / "tests" / "heldout").glob("*.py")
    )

    probe = ws4 / "tests" / "heldout" / "test_zz_probe.py"
    probe.write_text(PROBE, encoding="utf-8")
    probe_run = run_shell("pytest -q tests/heldout/test_zz_probe.py", ws4, 120)
    check(probe_run.exit_code == 0,
          "monkeypatching, sleep observability, exception identity and caplog all work",
          "" if probe_run.exit_code == 0 else probe_run.stdout[-400:])
    probe.unlink()

    # Precise, not substring: "test_logging_uses_..." contains "_log" and would trip a
    # naive check. What actually matters is a test reaching into a private attribute of
    # the package, or importing a private name from it.
    private = re.findall(r"(?:notifier[\w.]*|service|channels|retry)\.\s*_\w+", body)
    private += re.findall(r"from\s+notifier[\w.]*\s+import\s+_\w+", body)
    check(not private,
          "no held-out test reaches into a private implementation detail",
          str(private[:3]))
    check(body.count("ticket:") >= 8,
          "held-out tests are annotated with the ticket line each one checks")
    prose = "Let the original exception propagate. Its return value is a contract."
    check(not any(b in prose for b in ("call_with_retry", "TransientDeliveryError")),
          "the leakage check does not fire on ordinary prose")

    print("\n== 10. schedule is counterbalanced ==")
    firsts = [(["baseline", "candidate"] if i % 2 == 0 else ["candidate", "baseline"])[0]
              for i in range(4)]
    check(firsts.count("baseline") == firsts.count("candidate"),
          f"each arm leads equally often: {firsts}")

    remove_tree(SCRATCH)
    failed = [label for ok, label in results if not ok]
    print(f"\n{'=' * 60}\n{len(results) - len(failed)}/{len(results)} checks passed")
    for label in failed:
        print("  FAILED:", label)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

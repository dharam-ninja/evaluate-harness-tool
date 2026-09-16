"""A minimal coding agent for a local OpenAI-compatible model.

Shipped inside the package so it can be invoked as `python -m harness_eval.local_agent`
from any working directory -- a trial workspace is six levels below the repo root, and a
relative path from there is fragile. This is a HARNESS RUNNER, not evaluation logic: it
produces the work that gets graded, and grades nothing itself.

Exists because Claude Code refuses model ids it does not recognise, so it cannot drive
a local model. Rather than add a second AgentAdapter, this is a plain command:
`ShellAgentAdapter` already runs any command, feeds the ticket on stdin, copies the
harness instructions into the workspace and captures stdout. Nothing in the evaluator
changes.

The scaffold is deliberately fixed and identical for both arms:

    gather context -> ask the model -> write the file -> validate -> feed errors back

Only the presence of AGENTS.md differs. The model does not choose whether to validate;
it chooses what to write, and whether its second attempt is better than its first.

Emits stream-json events that `evidence.parse_stream` already understands, so files
inspected and tool calls land in the trial record with no new instrumentation.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

#: Files worth showing the model. Kept small: a 360M model has 8k of context.
CONTEXT_GLOBS = ("*.md", "*.html", "assets/*.css", "src/*/*.py", "tests/*/*.py")
MAX_FILE_CHARS = 2500
FENCE = re.compile(r"```(?:html|python|py)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def emit(event: dict[str, object]) -> None:
    """Write one stream-json line. The evaluator reads these for behavioural evidence."""
    print(json.dumps(event), flush=True)


def tool_use(name: str, tool_input: dict[str, object]) -> None:
    emit({"type": "assistant",
          "message": {"content": [{"type": "tool_use", "name": name, "input": tool_input}]}})


def read_file(path: Path) -> str:
    """Read a file and record that the agent looked at it."""
    tool_use("Read", {"file_path": str(path)})
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:MAX_FILE_CHARS]


def gather_context(workspace: Path) -> tuple[str, str | None]:
    """Collect repository context, and the harness instructions if this arm has them."""
    tool_use("Glob", {"path": ", ".join(CONTEXT_GLOBS)})
    guidance: str | None = None
    agents = workspace / "AGENTS.md"
    if agents.is_file():
        guidance = read_file(agents)

    parts: list[str] = []
    for pattern in CONTEXT_GLOBS:
        for path in sorted(workspace.glob(pattern)):
            if path.name == "AGENTS.md" or not path.is_file():
                continue
            parts.append(f"--- {path.relative_to(workspace).as_posix()} ---\n{read_file(path)}")
    return "\n\n".join(parts), guidance


def call_model(endpoint: str, model: str, messages: list[dict[str, str]], timeout: int) -> tuple[str, dict[str, int]]:
    url = endpoint.rstrip("/") + "/chat/completions"
    payload = {"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 2048}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer local"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = json.load(response)
    text = body["choices"][0]["message"]["content"] or ""
    usage = body.get("usage") or {}
    return text, {
        "input_tokens": int(usage.get("prompt_tokens") or 0),
        "output_tokens": int(usage.get("completion_tokens") or 0),
    }


def extract_html(text: str) -> str:
    """Pull the document out of the reply, whether or not it came in a code fence."""
    fenced = FENCE.search(text)
    candidate = fenced.group(1) if fenced else text
    start = candidate.lower().find("<!doctype")
    if start == -1:
        start = candidate.lower().find("<html")
    return (candidate[start:] if start != -1 else candidate).strip()


def extract_code(text: str) -> str:
    """Pull source out of the reply, stripping a markdown fence if there is one."""
    fenced = FENCE.search(text)
    return (fenced.group(1) if fenced else text).strip()


def verify(workspace: Path, command: str, timeout: int) -> tuple[bool, str]:
    """Run the project's own check. Recorded as a Bash tool call.

    The scaffold always runs this, for both arms. What the guidance can change is what
    the model does with the result, not whether the check happens.
    """
    tool_use("Bash", {"command": command})
    proc = subprocess.run(
        command, cwd=workspace, shell=True, capture_output=True,
        text=True, timeout=timeout, check=False)
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]


def extract_target(target: str, reply: str) -> str:
    """Choose the right extractor for the file being written."""
    return extract_html(reply) if target.endswith(".html") else extract_code(reply)


SYSTEM = (
    "You are a careful developer working in an existing project. "
    "Reply with one complete file and nothing else. No explanation, no commentary."
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--target", default="index.html")
    ap.add_argument("--test-target", default="",
                    help="If set, ask the model for tests too and write them here.")
    ap.add_argument("--verify", default="",
                    help="Command to run after writing. Defaults to the project validator.")
    ap.add_argument("--max-rounds", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    workspace = Path.cwd()
    ticket = sys.stdin.read().strip()
    started = time.monotonic()
    tokens = {"input_tokens": 0, "output_tokens": 0}
    turns = 0
    error: str | None = None
    fixed_after_validation = False
    tests_written = False

    try:
        context, guidance = gather_context(workspace)
        system = SYSTEM if guidance is None else f"{SYSTEM}\n\nProject guidance:\n{guidance}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content":
             f"Existing project files:\n\n{context}\n\nTicket:\n{ticket}\n\n"
             f"Write the complete contents of {args.target}."},
        ]

        verify_cmd = args.verify or f"{sys.executable} validate.py"
        target = workspace / args.target
        target.parent.mkdir(parents=True, exist_ok=True)
        ok = False
        for round_index in range(args.max_rounds):
            reply, used = call_model(args.endpoint, args.model, messages, args.timeout)
            turns += 1
            tokens["input_tokens"] += used["input_tokens"]
            tokens["output_tokens"] += used["output_tokens"]

            tool_use("Write", {"file_path": str(target)})
            target.write_text(extract_target(args.target, reply) + "\n", encoding="utf-8")

            ok, report = verify(workspace, verify_cmd, args.timeout)
            if ok:
                if round_index > 0:
                    fixed_after_validation = True
                break
            if round_index + 1 < args.max_rounds:
                messages += [
                    {"role": "assistant", "content": reply},
                    {"role": "user", "content":
                     f"Validation failed:\n{report}\nReturn the corrected complete document."},
                ]
        # The ticket asks for tests. A separate call, so "did it write tests" is an
        # observable fact rather than something inferred from the implementation file.
        if args.test_target:
            reply, used = call_model(args.endpoint, args.model, messages + [
                {"role": "assistant", "content": "(implementation written)"},
                {"role": "user", "content":
                 f"Now write focused tests for the new behaviour. Reply with the complete "
                 f"contents of {args.test_target} and nothing else."},
            ], args.timeout)
            turns += 1
            tokens["input_tokens"] += used["input_tokens"]
            tokens["output_tokens"] += used["output_tokens"]
            test_path = workspace / args.test_target
            test_path.parent.mkdir(parents=True, exist_ok=True)
            tool_use("Write", {"file_path": str(test_path)})
            test_path.write_text(extract_code(reply) + "\n", encoding="utf-8")
            tests_written = True
            ok, _ = verify(workspace, verify_cmd, args.timeout)

    except (urllib.error.URLError, subprocess.TimeoutExpired, OSError, KeyError, ValueError) as exc:
        error = f"{type(exc).__name__}: {exc}"

    elapsed = time.monotonic() - started
    emit({
        "type": "result",
        "subtype": "error" if error else "success",
        "is_error": bool(error),
        "result": error or "ok",
        "num_turns": turns,
        "duration_ms": int(elapsed * 1000),
        "duration_api_ms": int(elapsed * 1000),
        # A local model has no per-token price. 0.0 is the honest figure, not "unknown".
        "total_cost_usd": 0.0,
        "usage": {**tokens, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
        "modelUsage": {args.model: {"inputTokens": tokens["input_tokens"],
                                    "outputTokens": tokens["output_tokens"], "costUSD": 0.0}},
        "permission_denials": [],
        "fixed_after_validation": fixed_after_validation,
        "tests_written": tests_written,
    })
    return 1 if error else 0


if __name__ == "__main__":
    raise SystemExit(main())

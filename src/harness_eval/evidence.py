"""Per-trial evidence: patch, usage, timing, exit status.

Field names below were read off a live Claude Code 2.1.272 envelope (NOTES.md T+0:30),
not taken from the design brief -- the brief's guesses were close but the per-model
block is camelCase and `permission_denials` was missing entirely.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapters import ShellResult
from .models import Trial, TrialStatus, Usage
from .workspace import capture_patch, changed_files

#: Cache directory -> the tool that creates it. Presence proves the agent ran it.
TOOL_CACHES = {
    ".pytest_cache": "pytest",
    ".ruff_cache": "ruff",
    ".mypy_cache": "mypy",
}


def tools_run(workspace: Path) -> list[str]:
    """Which verification tools the agent ran, from the caches they leave behind.

    Must be called BEFORE the graders execute: they run the same three tools and would
    make every trial look verified.
    """
    return sorted(
        tool for cache, tool in TOOL_CACHES.items() if (workspace / cache).exists()
    )


#: Agent tools whose input names a file the agent looked at.
_INSPECT_TOOLS = {"Read": "file_path", "Grep": "path", "Glob": "path", "NotebookRead": "notebook_path"}


def count_hook_events(stdout: str) -> int:
    """How many hook lifecycle events the transcript carries.

    Requires --include-hook-events on the agent command. Zero means the hook never ran,
    which is a different finding from "the hook ran and changed nothing".
    """
    return sum(1 for line in stdout.splitlines() if '"hook_event_name"' in line or
               ('"type"' in line and '"hook' in line))


def parse_stream(stdout: str) -> tuple[dict[str, int], list[str]]:
    """Extract tool usage from a stream-json transcript.

    Returns (tool name -> call count, files the agent inspected). Empty for a plain
    `--output-format json` run, which carries no per-turn detail.
    """
    calls: dict[str, int] = {}
    seen: set[str] = set()
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{") or '"tool_use"' not in line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (event.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = str(block.get("name", "?"))
            calls[name] = calls.get(name, 0) + 1
            key = _INSPECT_TOOLS.get(name)
            if key:
                target = (block.get("input") or {}).get(key)
                if isinstance(target, str):
                    seen.add(target.replace("\\", "/").split("/")[-1])
    return calls, sorted(seen)


def _as_int(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def parse_envelope(stdout: str) -> tuple[Usage, dict[str, Any] | None]:
    """Parse the agent's JSON result envelope.

    Every field is optional and an absent one stays None. Defaulting to 0 would make a
    run that reported nothing indistinguishable from a run that cost nothing, and the
    cost dimension is a comparison of small numbers.
    """
    text = stdout.strip()
    if not text:
        return Usage(), None

    envelope: dict[str, Any] | None = None
    try:
        envelope = json.loads(text)
    except json.JSONDecodeError:
        # stream-json, or a banner ahead of the payload: take the last JSON object.
        for line in reversed(text.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    envelope = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

    if not isinstance(envelope, dict):
        return Usage(), None

    usage_block = envelope.get("usage") or {}
    return (
        Usage(
            total_cost_usd=envelope.get("total_cost_usd"),
            input_tokens=_as_int(usage_block.get("input_tokens")),
            output_tokens=_as_int(usage_block.get("output_tokens")),
            cache_creation_input_tokens=_as_int(usage_block.get("cache_creation_input_tokens")),
            cache_read_input_tokens=_as_int(usage_block.get("cache_read_input_tokens")),
            num_turns=_as_int(envelope.get("num_turns")),
            duration_ms=_as_int(envelope.get("duration_ms")),
            duration_api_ms=_as_int(envelope.get("duration_api_ms")),
            model_usage=envelope.get("modelUsage") or {},
            permission_denials=envelope.get("permission_denials") or [],
            is_error=envelope.get("is_error"),
            subtype=envelope.get("subtype"),
            session_id=envelope.get("session_id"),
        ),
        envelope,
    )


def collect(
    task_id: str,
    harness_name: str,
    rep: int,
    workspace: Path,
    trial_dir: Path,
    shell: ShellResult,
) -> Trial:
    """Turn a finished agent run into a Trial, and write its artifacts."""
    files = changed_files(workspace)
    ran = tools_run(workspace)
    calls, inspected = parse_stream(shell.stdout)
    hooks = count_hook_events(shell.stdout)
    touched_tests = [f for f in files if f.startswith("tests/") or "/tests/" in f]
    patch_bytes = capture_patch(workspace, trial_dir / "patch.diff")
    usage, envelope = parse_envelope(shell.stdout)

    if envelope is not None:
        (trial_dir / "transcript.json").write_text(
            json.dumps(envelope, indent=2), encoding="utf-8"
        )

    if shell.timed_out:
        status = TrialStatus.TIMEOUT
        error: str | None = f"exceeded timeout after {shell.wall_clock_s:.0f}s"
    elif usage.permission_denials and patch_bytes == 0:
        # Denied AND produced nothing. A blocked trial is cheap and empty, so without
        # this it would read as a fast, efficient failure and drag the cost average down.
        status = TrialStatus.BLOCKED
        error = f"{len(usage.permission_denials)} permission denial(s), no changes made"
    elif shell.exit_code not in (0, None) or usage.is_error:
        status = TrialStatus.ERROR
        error = (shell.stderr or "").strip()[-500:] or f"exit code {shell.exit_code}"
    else:
        status = TrialStatus.COMPLETED
        error = None

    result = Trial(
        task_id=task_id,
        harness=harness_name,
        rep=rep,
        status=status,
        exit_code=shell.exit_code,
        wall_clock_s=round(shell.wall_clock_s, 2),
        usage=usage,
        files_changed=files,
        patch_bytes=patch_bytes,
        tools_run=ran,
        tool_calls=calls,
        hook_events=hooks,
        files_inspected=inspected,
        tests_modified=touched_tests,
        error=error,
        workspace=str(workspace),
        trial_dir=str(trial_dir),
    )
    write_result(trial_dir, result)
    return result


def write_result(trial_dir: Path, result: Trial) -> None:
    trial_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "result.json").write_text(
        result.model_dump_json(indent=2), encoding="utf-8"
    )

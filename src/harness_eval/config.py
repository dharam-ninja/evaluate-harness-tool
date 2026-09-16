"""YAML loading and validation into the pydantic models in models.py.

All relative paths resolve against the config file's directory, never the cwd, so
`harness-eval evaluate examples/eval.yaml` behaves the same from anywhere.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import AgentHarness, EvalConfig, Grader, Task


class ConfigError(Exception):
    """Malformed configuration. Raised with the offending file and field."""


#: ${VAR} or ${VAR:-default}
_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def expand_env(value: Any, where: str) -> Any:
    """Substitute ${VAR} and ${VAR:-default} through any string in the config.

    An endpoint URL or an API key belongs in the environment, not in a file that gets
    committed. A reference with no value and no default is an error rather than an empty
    string: silently substituting "" would produce a run that looks configured and is not.
    """
    if isinstance(value, dict):
        return {k: expand_env(v, f"{where}.{k}") for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v, f"{where}[{i}]") for i, v in enumerate(value)]
    if not isinstance(value, str):
        return value

    missing: list[str] = []

    def _sub(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        found = os.environ.get(name)
        if found:
            return found
        if default is not None:
            return default
        missing.append(name)
        return ""

    result = _ENV_REF.sub(_sub, value)
    if missing:
        raise ConfigError(
            f"{where}: environment variable(s) {', '.join(missing)} are not set and have "
            f"no default. Set them, or write ${{NAME:-fallback}} in the config."
        )
    return result


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"{path}: no such file")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML -- {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected a mapping at the top level")
    # `x-` keys exist only to anchor reusable YAML values.
    stripped = {k: v for k, v in data.items() if not str(k).startswith("x-")}
    result: dict[str, Any] = expand_env(stripped, str(path))
    return result


def _load_task(path: Path, root: Path) -> Task:
    raw = _read_yaml(path)
    try:
        task = Task(**raw)
    except ValidationError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    task.acceptance_tests = (root / task.acceptance_tests).resolve()
    task.heldout_tests = (root / task.heldout_tests).resolve()
    for label, p in (("acceptance_tests", task.acceptance_tests), ("heldout_tests", task.heldout_tests)):
        if not p.is_dir():
            raise ConfigError(f"{path}: {label} -> {p} is not a directory")
    return task


def load_config(path: str | Path) -> EvalConfig:
    """Load an eval.yaml plus every task it names."""
    cfg_path = Path(path).resolve()
    root = cfg_path.parent.parent if cfg_path.parent.name == "examples" else cfg_path.parent
    raw = _read_yaml(cfg_path)

    harnesses: dict[str, AgentHarness] = {}
    for name, spec in (raw.get("harnesses") or {}).items():
        try:
            h = AgentHarness(name=name, **spec)
        except ValidationError as exc:
            raise ConfigError(f"{cfg_path}: harness '{name}': {exc}") from exc
        if h.instructions is not None:
            h.instructions = (root / h.instructions).resolve()
            if not h.instructions.is_file():
                raise ConfigError(f"{cfg_path}: harness '{name}': instructions -> {h.instructions} not found")
        if h.config_dir is not None:
            h.config_dir = (root / h.config_dir).resolve()
            if not h.config_dir.is_dir():
                raise ConfigError(
                    f"{cfg_path}: harness '{name}': config_dir -> {h.config_dir} is not a directory"
                )
        harnesses[name] = h

    for required in ("baseline", "candidate"):
        if required not in harnesses:
            raise ConfigError(f"{cfg_path}: harnesses must define '{required}'")

    tasks = [_load_task((cfg_path.parent / "tasks" / f"{tid}.yaml"), root) for tid in (raw.get("tasks") or [])]
    if not tasks:
        raise ConfigError(f"{cfg_path}: no tasks listed")

    try:
        graders = [Grader(**g) for g in (raw.get("graders") or [])]
    except ValidationError as exc:
        raise ConfigError(f"{cfg_path}: graders: {exc}") from exc
    if not any(g.critical for g in graders):
        raise ConfigError(f"{cfg_path}: at least one grader must be critical")

    # Dimensions are declared by the config, not hardcoded here. That keeps the hard
    # constraint (adding a grader is a YAML edit) while still catching a typo'd
    # dimension, which would otherwise silently create a one-grader dimension in the
    # report and quietly drop that grader out of the one it was meant to join.
    dimensions = list(raw.get("dimensions") or [])
    if not dimensions:
        raise ConfigError(f"{cfg_path}: 'dimensions' must list the dimensions graders may use")
    for g in graders:
        if g.dimension not in dimensions:
            raise ConfigError(
                f"{cfg_path}: grader '{g.id}': unknown dimension '{g.dimension}' "
                f"(declared dimensions: {', '.join(dimensions)})"
            )
    seen: set[str] = set()
    for g in graders:
        if g.id in seen:
            raise ConfigError(f"{cfg_path}: duplicate grader id '{g.id}'")
        seen.add(g.id)

    repo = (root / raw["repo"]).resolve() if "repo" in raw else None
    if repo is None or not repo.is_dir():
        raise ConfigError(f"{cfg_path}: repo -> {repo} is not a directory")

    try:
        return EvalConfig(
            repo=repo,
            change=raw.get("change", ""),
            harnesses=harnesses,
            tasks=tasks,
            graders=graders,
            dimensions=dimensions,
            intended_difference=list(raw.get("intended_difference") or ["instructions"]),
            reps=raw.get("reps", 2),
            timeout_s=raw.get("timeout_s", 600),
            jobs=raw.get("jobs", 1),
            source=cfg_path,
        )
    except ValidationError as exc:
        raise ConfigError(f"{cfg_path}: {exc}") from exc

"""Config loading and validation, including malformed-config rejection.

Malformed config is itself a reliability risk: a typo that silently changes what runs
produces a confident report about an experiment nobody intended. Every case here is a
mistake that would otherwise survive into a run.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from harness_eval.config import ConfigError, load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "examples" / "eval.yaml"


def _absolute(value: str) -> str:
    return str((REPO_ROOT / value).resolve())


def _write(tmp_path: Path, mutate: object = None) -> Path:
    """Copy the real example config into tmp_path, optionally mutating it first.

    Every path is rewritten to an absolute one pointing back at the real repo, so the
    only thing that differs from a working config is the mutation under test. Without
    that, an unrelated "file not found" fires first and the test passes for the wrong
    reason.
    """
    raw = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    raw.pop("x-command", None)
    raw["repo"] = _absolute(raw["repo"])
    for harness in raw["harnesses"].values():
        if harness.get("instructions"):
            harness["instructions"] = _absolute(harness["instructions"])
    if callable(mutate):
        mutate(raw)

    examples = tmp_path / "examples"
    (examples / "tasks").mkdir(parents=True)
    for task_file in (EXAMPLE.parent / "tasks").glob("*.yaml"):
        task_raw = yaml.safe_load(task_file.read_text(encoding="utf-8"))
        for key in ("acceptance_tests", "heldout_tests"):
            if isinstance(task_raw.get(key), str) and task_raw[key] != "TODO":
                task_raw[key] = _absolute(task_raw[key])
        (examples / "tasks" / task_file.name).write_text(
            yaml.safe_dump(task_raw), encoding="utf-8"
        )
    cfg = examples / "eval.yaml"
    cfg.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return cfg


# --------------------------------------------------------------------------- happy path


def test_example_config_loads() -> None:
    cfg = load_config(EXAMPLE)
    assert set(cfg.harnesses) == {"baseline", "candidate"}
    # Not a fixed list: the suite grows. The invariant is that every task the config
    # names actually resolves to both of its test directories.
    assert cfg.tasks
    for task in cfg.tasks:
        assert task.acceptance_tests.is_dir(), task.id
        assert task.heldout_tests.is_dir(), task.id
        assert task.prompt.strip(), task.id
    assert {g.id for g in cfg.graders} == {
        "acceptance", "heldout", "regressions", "lint", "types"
    }


def test_relative_paths_resolve_against_the_config_file_not_the_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`harness-eval evaluate examples/eval.yaml` must behave the same from anywhere."""
    monkeypatch.chdir(tmp_path)
    cfg = load_config(EXAMPLE)
    assert cfg.repo.is_absolute() and cfg.repo.is_dir()
    assert cfg.tasks[0].acceptance_tests.is_absolute()
    assert cfg.tasks[0].heldout_tests.is_absolute()
    assert cfg.harnesses["candidate"].instructions is not None
    assert cfg.harnesses["candidate"].instructions.is_file()


def test_the_two_arms_differ_only_in_instructions() -> None:
    """If the arms were identical the run would measure nothing at real cost."""
    cfg = load_config(EXAMPLE)
    base, cand = cfg.baseline, cfg.candidate
    assert base.command == cand.command
    assert base.model == cand.model
    assert base.instructions != cand.instructions


# --------------------------------------------------------------------------- rejection


def test_unknown_dimension_is_rejected(tmp_path: Path) -> None:
    def mutate(raw: dict) -> None:
        raw["graders"][0]["dimension"] = "corectness"  # typo

    with pytest.raises(ConfigError) as exc:
        load_config(_write(tmp_path, mutate))
    assert "unknown dimension" in str(exc.value)
    assert "corectness" in str(exc.value)


def test_missing_dimensions_block_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="dimensions"):
        load_config(_write(tmp_path, lambda raw: raw.pop("dimensions")))


def test_missing_task_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as exc:
        load_config(_write(tmp_path, lambda raw: raw["tasks"].append("no-such-task")))
    assert "no-such-task" in str(exc.value)


def test_missing_harness_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="candidate"):
        load_config(_write(tmp_path, lambda raw: raw["harnesses"].pop("candidate")))


def test_config_with_no_critical_grader_is_rejected(tmp_path: Path) -> None:
    """Without a critical grader every task would score PASS vacuously."""

    def mutate(raw: dict) -> None:
        for g in raw["graders"]:
            g["critical"] = False

    with pytest.raises(ConfigError, match="critical"):
        load_config(_write(tmp_path, mutate))


def test_duplicate_grader_id_is_rejected(tmp_path: Path) -> None:
    def mutate(raw: dict) -> None:
        raw["graders"].append(dict(raw["graders"][0]))

    with pytest.raises(ConfigError, match="duplicate grader id"):
        load_config(_write(tmp_path, mutate))


def test_missing_repo_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="repo"):
        load_config(_write(tmp_path, lambda raw: raw.update(repo="does/not/exist")))


def test_instructions_pointing_nowhere_is_rejected(tmp_path: Path) -> None:
    """A silently missing AGENTS.md would make the candidate arm identical to baseline."""

    def mutate(raw: dict) -> None:
        raw["harnesses"]["candidate"]["instructions"] = "examples/harnesses/candidate/GONE.md"

    with pytest.raises(ConfigError, match="instructions"):
        load_config(_write(tmp_path, mutate))


def test_invalid_yaml_names_the_file(tmp_path: Path) -> None:
    bad = tmp_path / "eval.yaml"
    bad.write_text("harnesses: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(bad)
    assert str(bad) in str(exc.value)


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="no such file"):
        load_config(tmp_path / "nope.yaml")


# --------------------------------------------------- per-harness model / endpoint


MODELS = REPO_ROOT / "examples" / "eval-models.yaml"


def test_env_reference_is_expanded(monkeypatch: pytest.MonkeyPatch) -> None:
    """The endpoint lives in the environment, never in a committed file."""
    monkeypatch.setenv("HARNESS1_MODEL_URL", "https://llama.internal/v1")
    cfg = load_config(MODELS)
    assert cfg.baseline.endpoint == "https://llama.internal/v1"
    assert "https://llama.internal/v1" in cfg.baseline.description


def test_env_reference_default_is_used_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HARNESS1_MODEL_URL", "https://x/v1")
    monkeypatch.delenv("HARNESS1_MODEL", raising=False)
    assert load_config(MODELS).baseline.model == "llama-3.3-70b-instruct"


def test_an_explicit_model_overrides_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HARNESS1_MODEL_URL", "https://x/v1")
    monkeypatch.setenv("HARNESS1_MODEL", "llama-4-maverick")
    assert load_config(MODELS).baseline.model == "llama-4-maverick"


def test_a_missing_variable_with_no_default_is_a_loud_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Substituting "" would produce a run that looks configured and silently is not."""
    monkeypatch.delenv("HARNESS1_MODEL_URL", raising=False)
    with pytest.raises(ConfigError) as exc:
        load_config(MODELS)
    assert "HARNESS1_MODEL_URL" in str(exc.value)
    assert "not set" in str(exc.value)


def test_the_two_arms_differ_only_in_the_declared_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HARNESS1_MODEL_URL", "https://x/v1")
    cfg = load_config(MODELS)
    assert set(cfg.intended_difference) == {"model", "endpoint"}
    b, c = cfg.baseline, cfg.candidate
    for field in ("command", "budget", "instructions"):
        assert getattr(b, field) == getattr(c, field), field
    for field in cfg.intended_difference:
        assert getattr(b, field) != getattr(c, field), field


def test_the_endpoint_reaches_the_trial_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-harness, so the second arm cannot inherit the first arm's provider."""
    from harness_eval.adapters import ShellAgentAdapter

    monkeypatch.setenv("HARNESS1_MODEL_URL", "https://llama.internal/v1")
    cfg = load_config(MODELS)
    captured: dict[str, dict[str, str] | None] = {}

    def fake_run_shell(command, cwd, timeout_s, stdin_text=None, env=None):  # type: ignore[no-untyped-def]
        captured["env"] = env
        from harness_eval.adapters import ShellResult

        return ShellResult(0, "{}", "", 0.1, False)

    monkeypatch.setattr("harness_eval.adapters.run_shell", fake_run_shell)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        (ws / "AGENTS.md").unlink(missing_ok=True)
        ShellAgentAdapter().run(cfg.tasks[0], cfg.baseline, ws, ws, 60)
    assert (captured["env"] or {}).get("ANTHROPIC_BASE_URL") == "https://llama.internal/v1"


def test_a_harness_without_an_endpoint_sets_no_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from harness_eval.adapters import ShellAgentAdapter, ShellResult

    monkeypatch.setenv("HARNESS1_MODEL_URL", "https://x/v1")
    cfg = load_config(MODELS)
    captured: dict[str, dict[str, str] | None] = {}

    def fake_run_shell(command, cwd, timeout_s, stdin_text=None, env=None):  # type: ignore[no-untyped-def]
        captured["env"] = env
        return ShellResult(0, "{}", "", 0.1, False)

    monkeypatch.setattr("harness_eval.adapters.run_shell", fake_run_shell)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        ShellAgentAdapter().run(cfg.tasks[0], cfg.candidate, ws, ws, 60)
    assert "ANTHROPIC_BASE_URL" not in (captured["env"] or {})


def test_provider_is_reported_for_both_arms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HARNESS1_MODEL_URL", "https://llama.internal/v1")
    cfg = load_config(MODELS)
    assert cfg.baseline.provider == "https://llama.internal/v1"
    assert cfg.candidate.provider == "default (CLI-configured)"

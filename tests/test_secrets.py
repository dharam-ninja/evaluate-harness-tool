"""A credential passed through a harness `env` block must never reach a run artifact.

`${VAR}` is expanded at config-load time, so the plaintext value is present in memory by
the time a manifest is written. The manifest lands in a run directory that .gitignore
re-includes by name for demonstration samples, which means anything recorded there is one
`git add` away from being published. These tests use a canary string and assert it is
absent from everything written to disk.
"""

from __future__ import annotations

import json

import pytest

from harness_eval.cli import REDACTED, _harness_dump, _shown
from harness_eval.config import expand_env
from harness_eval.models import AgentHarness

CANARY = "sk-ant-CANARY-do-not-record-0123456789"


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch) -> AgentHarness:
    monkeypatch.setenv("CANARY_KEY", CANARY)
    raw = {
        "command": "agent --run",
        "model": "claude-haiku-4-5",
        "env": {"ANTHROPIC_AUTH_TOKEN": "${CANARY_KEY}", "SOME_FLAG": "plain-value"},
    }
    return AgentHarness(**expand_env(raw, "test-config"))


def test_expansion_still_gives_the_agent_the_real_value(harness: AgentHarness) -> None:
    """Redaction is for what is written down, not for what the subprocess receives."""
    assert harness.env["ANTHROPIC_AUTH_TOKEN"] == CANARY


def test_the_manifest_record_of_a_harness_carries_no_secret(harness: AgentHarness) -> None:
    dumped = json.dumps(_harness_dump(harness))
    assert CANARY not in dumped
    assert dumped.count(REDACTED) == 2


def test_variable_names_survive_so_a_run_stays_reproducible(harness: AgentHarness) -> None:
    """Dropping the names too would hide which variables a reader has to set."""
    env = _harness_dump(harness)["env"]
    assert set(env) == {"ANTHROPIC_AUTH_TOKEN", "SOME_FLAG"}


def test_the_fairness_block_carries_no_secret(harness: AgentHarness) -> None:
    """`env` can be the declared variable under test, which routes it through _shown."""
    assert CANARY not in json.dumps(_shown(harness.env))


def test_non_dict_harness_fields_are_untouched() -> None:
    """Redaction must not swallow the fields the fairness record exists to compare."""
    assert _shown("claude-haiku-4-5") == "claude-haiku-4-5"
    assert _shown(None) is None
    assert _shown(0.5) == 0.5

"""Held-out verification for add-retry. Never copied into the agent's workspace.

The ticket states the backoff contract. The acceptance suite checks that retries happen
at all; it never checks how many times the caller waits, or that the caller sees the
real exception rather than a wrapper.
"""

from __future__ import annotations

import pytest

from demo.retry import TransientError, call_with_retry


def test_the_original_exception_reaches_the_caller_not_a_wrapper() -> None:
    marker = TransientError("the original")

    def op() -> None:
        raise marker

    with pytest.raises(TransientError) as exc:
        call_with_retry(op, attempts=2, sleep=lambda _: None)
    assert exc.value is marker


def test_no_wait_happens_after_the_final_attempt() -> None:
    waits: list[float] = []

    def op() -> None:
        raise TransientError("always")

    with pytest.raises(TransientError):
        call_with_retry(op, attempts=3, sleep=waits.append)
    assert len(waits) == 2  # 3 attempts means 2 gaps, not 3


def test_a_first_time_success_never_waits() -> None:
    waits: list[float] = []
    call_with_retry(lambda: "ok", attempts=3, sleep=waits.append)
    assert waits == []


def test_a_single_attempt_means_no_retry_and_no_wait() -> None:
    waits: list[float] = []
    calls = {"n": 0}

    def op() -> None:
        calls["n"] += 1
        raise TransientError("always")

    with pytest.raises(TransientError):
        call_with_retry(op, attempts=1, sleep=waits.append)
    assert calls["n"] == 1
    assert waits == []

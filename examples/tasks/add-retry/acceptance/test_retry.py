"""Acceptance tests for add-retry. Adequate coverage -- this is the control task."""

from __future__ import annotations

import pytest

from demo.retry import TransientError, call_with_retry


def _flaky(failures: int):
    calls = {"n": 0}

    def op() -> str:
        calls["n"] += 1
        if calls["n"] <= failures:
            raise TransientError("not yet")
        return "ok"

    op.calls = calls  # type: ignore[attr-defined]
    return op


def test_succeeds_without_retrying_when_the_first_attempt_works() -> None:
    assert call_with_retry(_flaky(0), sleep=lambda _: None) == "ok"


def test_retries_a_transient_failure_and_then_succeeds() -> None:
    op = _flaky(2)
    assert call_with_retry(op, attempts=3, sleep=lambda _: None) == "ok"
    assert op.calls["n"] == 3


def test_gives_up_after_the_attempt_limit() -> None:
    op = _flaky(99)
    with pytest.raises(TransientError):
        call_with_retry(op, attempts=3, sleep=lambda _: None)
    assert op.calls["n"] == 3


def test_does_not_retry_an_error_outside_retry_on() -> None:
    calls = {"n": 0}

    def op() -> None:
        calls["n"] += 1
        raise KeyError("fatal")

    with pytest.raises(KeyError):
        call_with_retry(op, attempts=3, sleep=lambda _: None)
    assert calls["n"] == 1

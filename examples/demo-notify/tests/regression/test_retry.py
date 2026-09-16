"""Pre-existing retry helper behaviour. Must keep working."""

from __future__ import annotations

import pytest

from notifier.errors import PermanentDeliveryError, TransientDeliveryError
from notifier.retry import call_with_retry


def test_a_successful_call_returns_its_value() -> None:
    assert call_with_retry(lambda: "ok", sleep=lambda _: None) == "ok"


def test_transient_failures_are_retried_up_to_the_limit() -> None:
    calls = {"n": 0}

    def op() -> str:
        calls["n"] += 1
        raise TransientDeliveryError("nope")

    with pytest.raises(TransientDeliveryError):
        call_with_retry(op, attempts=3, sleep=lambda _: None)
    assert calls["n"] == 3


def test_permanent_failures_are_not_retried() -> None:
    calls = {"n": 0}

    def op() -> str:
        calls["n"] += 1
        raise PermanentDeliveryError("no")

    with pytest.raises(PermanentDeliveryError):
        call_with_retry(op, attempts=3, sleep=lambda _: None)
    assert calls["n"] == 1


def test_no_wait_after_the_final_attempt() -> None:
    waits: list[float] = []

    def op() -> str:
        raise TransientDeliveryError("nope")

    with pytest.raises(TransientDeliveryError):
        call_with_retry(op, attempts=3, sleep=waits.append)
    assert len(waits) == 2

"""Retry helper shared by every outbound channel."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from notifier.errors import TransientDeliveryError
from notifier.logging_utils import get_logger

T = TypeVar("T")

_log = get_logger(__name__)


def call_with_retry(
    operation: Callable[[], T],
    attempts: int = 3,
    delay_s: float = 0.01,
    sleep: Callable[[float], None] | None = None,
) -> T:
    """Call `operation`, retrying transient failures.

    Makes at most `attempts` calls in total. Waits `delay_s` between attempts and not
    after the final one. Only `TransientDeliveryError` is retried; anything else
    propagates immediately. When every attempt fails the last exception is re-raised
    unchanged.

    `sleep` defaults to `time.sleep`, resolved when the call is made rather than bound
    at import, so a test can replace it on this module.
    """
    wait = sleep if sleep is not None else time.sleep
    last: TransientDeliveryError | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except TransientDeliveryError as exc:
            last = exc
            _log.warning("attempt %s of %s failed: %s", attempt, attempts, exc)
            if attempt < attempts:
                wait(delay_s)
    assert last is not None
    raise last

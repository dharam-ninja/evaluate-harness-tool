"""Retry helpers for flaky outbound calls."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class TransientError(Exception):
    """A failure that is expected to succeed on a later attempt."""


def call_with_retry(
    operation: Callable[[], T],
    attempts: int = 3,
    retry_on: tuple[type[BaseException], ...] = (TransientError,),
    sleep: Callable[[float], None] = time.sleep,
    backoff_s: float = 0.01,
) -> T:
    """Call `operation` and return its result.

    `attempts`, `retry_on`, `sleep` and `backoff_s` are accepted but not yet honoured.
    """
    return operation()

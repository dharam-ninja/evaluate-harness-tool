"""Pre-existing retry behaviour."""

from __future__ import annotations

import pytest

from demo.retry import TransientError, call_with_retry


def test_a_successful_call_returns_its_value() -> None:
    assert call_with_retry(lambda: 42) == 42


def test_the_operation_result_is_passed_through_untouched() -> None:
    sentinel = object()
    assert call_with_retry(lambda: sentinel) is sentinel


def test_transient_error_is_importable() -> None:
    assert issubclass(TransientError, Exception)


def test_an_unhandled_error_propagates() -> None:
    def boom() -> None:
        raise KeyError("nope")

    with pytest.raises(KeyError):
        call_with_retry(boom)

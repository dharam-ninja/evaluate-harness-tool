"""Held-out verification for notify-fallback. Never copied into the agent's workspace.

Every test maps to a behaviour the ticket states. Nothing here is undiscoverable: the
retry semantics, the transient/permanent split, the fallback rule, the exception rule
and the logging convention are all either in the ticket or in the package itself.
"""

from __future__ import annotations

import inspect
import logging

import pytest

from notifier import channels, retry
from notifier.errors import PermanentDeliveryError, TransientDeliveryError
from notifier.service import send_notification

RECIPIENT = {"email": "a@b.com", "phone": "+15550000"}
NO_PHONE = {"email": "a@b.com"}


def _counting(exc: Exception | None, receipt: str = "ok"):
    calls = {"n": 0}

    def transport(target: str, message: str) -> str:
        calls["n"] += 1
        if exc is not None:
            raise exc
        return receipt

    transport.calls = calls  # type: ignore[attr-defined]
    return transport


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Capture every wait so tests never actually sleep."""
    waits: list[float] = []
    monkeypatch.setattr(retry.time, "sleep", waits.append)
    return waits


# ticket: "Retry a failed email delivery, making at most 3 attempts in total."


def test_email_is_attempted_exactly_three_times(monkeypatch: pytest.MonkeyPatch) -> None:
    email = _counting(TransientDeliveryError("down"))
    monkeypatch.setattr(channels, "email_transport", email)
    monkeypatch.setattr(channels, "sms_transport", lambda n, m: "sms")
    send_notification(RECIPIENT, "hi")
    assert email.calls["n"] == 3


def test_a_first_time_success_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    email = _counting(None, "email-receipt")
    monkeypatch.setattr(channels, "email_transport", email)
    assert send_notification(RECIPIENT, "hi") == "email-receipt"
    assert email.calls["n"] == 1


# ticket: "Wait between attempts. Do not wait after the final attempt."


def test_no_wait_after_the_final_attempt(
    monkeypatch: pytest.MonkeyPatch, _no_real_sleep: list[float]
) -> None:
    monkeypatch.setattr(channels, "email_transport", _counting(TransientDeliveryError("d")))
    monkeypatch.setattr(channels, "sms_transport", lambda n, m: "sms")
    send_notification(RECIPIENT, "hi")
    # 3 email attempts means 2 gaps, and the successful sms adds none.
    assert len(_no_real_sleep) == 2


# ticket: "A failure the provider will never accept must not be retried at all."


def test_a_permanent_email_failure_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    email = _counting(PermanentDeliveryError("rejected"))
    monkeypatch.setattr(channels, "email_transport", email)
    monkeypatch.setattr(channels, "sms_transport", lambda n, m: "sms")
    send_notification(RECIPIENT, "hi")
    assert email.calls["n"] == 1


# ticket: "fall back to SMS ... under the same retry rules."


def test_sms_is_also_retried_three_times(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(channels, "email_transport", _counting(TransientDeliveryError("d")))
    sms = _counting(TransientDeliveryError("sms down"))
    monkeypatch.setattr(channels, "sms_transport", sms)
    with pytest.raises(TransientDeliveryError):
        send_notification(RECIPIENT, "hi")
    assert sms.calls["n"] == 3


# ticket: "If the recipient has no phone number, there is nothing to fall back to."


def test_without_a_phone_number_the_email_failure_reaches_the_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = TransientDeliveryError("email down")
    monkeypatch.setattr(channels, "email_transport", _counting(marker))
    with pytest.raises(TransientDeliveryError) as exc:
        send_notification(NO_PHONE, "hi")
    assert exc.value is marker


# ticket: "the caller must receive the exception the SMS channel raised, not a new
#          exception wrapping it."


def test_the_sms_exception_reaches_the_caller_unwrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = TransientDeliveryError("sms is the last word")
    monkeypatch.setattr(channels, "email_transport", _counting(TransientDeliveryError("e")))
    monkeypatch.setattr(channels, "sms_transport", _counting(marker))
    with pytest.raises(TransientDeliveryError) as exc:
        send_notification(RECIPIENT, "hi")
    assert exc.value is marker


# ticket: "Follow this package's existing logging conventions."
# notifier/logging_utils.py: every module gets its logger from get_logger(__name__),
# which prefixes the name with "notifier.".


def test_logging_uses_the_package_convention(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(channels, "email_transport", _counting(TransientDeliveryError("d")))
    monkeypatch.setattr(channels, "sms_transport", lambda n, m: "sms")
    with caplog.at_level(logging.DEBUG):
        send_notification(RECIPIENT, "hi")
    names = {r.name for r in caplog.records}
    assert names, "nothing was logged at all"
    assert all(n.startswith("notifier.") for n in names), names


def test_a_retry_is_logged_as_a_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(channels, "email_transport", _counting(TransientDeliveryError("d")))
    monkeypatch.setattr(channels, "sms_transport", lambda n, m: "sms")
    with caplog.at_level(logging.DEBUG):
        send_notification(RECIPIENT, "hi")
    assert any(r.levelno >= logging.WARNING for r in caplog.records)


# ticket: "keeps its signature and its return value: other code calls it."


def test_the_public_signature_is_unchanged() -> None:
    assert list(inspect.signature(send_notification).parameters) == ["recipient", "message"]


def test_the_return_value_is_still_the_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(channels, "email_transport", lambda a, m: "the-receipt")
    assert send_notification(RECIPIENT, "hi") == "the-receipt"


# --- independent checks added for the high-process experiment -------------------------
# Each isolates one clause of the contract that was previously only covered incidentally.


def test_sms_is_not_attempted_when_email_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """ticket: fallback is for when email fails, so a success must not also send sms."""
    sms = _counting(None, "sms")
    monkeypatch.setattr(channels, "email_transport", _counting(None, "email"))
    monkeypatch.setattr(channels, "sms_transport", sms)
    send_notification(RECIPIENT, "hi")
    assert sms.calls["n"] == 0


def test_the_fallback_path_returns_the_sms_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    """ticket: 'keeps ... its return value' -- the receipt, whichever channel produced it."""
    monkeypatch.setattr(channels, "email_transport", _counting(TransientDeliveryError("d")))
    monkeypatch.setattr(channels, "sms_transport", _counting(None, "sms-receipt"))
    assert send_notification(RECIPIENT, "hi") == "sms-receipt"


def test_a_wait_actually_happens_between_email_attempts(
    monkeypatch: pytest.MonkeyPatch, _no_real_sleep: list[float]
) -> None:
    """ticket: 'Wait between attempts' -- not merely 'do not wait after the last'."""
    monkeypatch.setattr(channels, "email_transport", _counting(TransientDeliveryError("d")))
    monkeypatch.setattr(channels, "sms_transport", lambda n, m: "sms")
    send_notification(RECIPIENT, "hi")
    assert len(_no_real_sleep) >= 1
    assert all(w > 0 for w in _no_real_sleep), _no_real_sleep


def test_a_permanent_sms_failure_reaches_the_caller_unwrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ticket: the caller receives the exception the SMS channel raised, whichever kind."""
    marker = PermanentDeliveryError("bad number")
    monkeypatch.setattr(channels, "email_transport", _counting(TransientDeliveryError("d")))
    monkeypatch.setattr(channels, "sms_transport", _counting(marker))
    with pytest.raises(PermanentDeliveryError) as exc:
        send_notification(RECIPIENT, "hi")
    assert exc.value is marker


def test_the_public_import_path_is_unchanged() -> None:
    """ticket: 'other code calls it' -- the import other code uses must still work."""
    import importlib

    module = importlib.import_module("notifier.service")
    assert hasattr(module, "send_notification")
    assert callable(module.send_notification)


def test_send_notification_still_returns_a_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(channels, "email_transport", lambda a, m: "receipt")
    assert isinstance(send_notification(RECIPIENT, "hi"), str)

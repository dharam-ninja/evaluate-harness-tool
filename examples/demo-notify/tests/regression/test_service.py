"""Pre-existing public API of send_notification. Must keep working."""

from __future__ import annotations

import pytest

from notifier import channels
from notifier.service import send_notification


def test_send_notification_returns_the_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(channels, "email_transport", lambda a, m: "r-1")
    assert send_notification({"email": "a@b.com"}, "hi") == "r-1"


def test_send_notification_takes_a_recipient_mapping_and_a_message() -> None:
    import inspect

    params = list(inspect.signature(send_notification).parameters)
    assert params == ["recipient", "message"]


def test_the_package_still_imports_cleanly() -> None:
    import importlib

    for name in ("notifier", "notifier.service", "notifier.channels",
                 "notifier.errors", "notifier.retry", "notifier.logging_utils"):
        assert importlib.import_module(name) is not None


def test_the_error_hierarchy_is_intact() -> None:
    from notifier.errors import (
        NotificationError,
        PermanentDeliveryError,
        TransientDeliveryError,
    )

    assert issubclass(TransientDeliveryError, NotificationError)
    assert issubclass(PermanentDeliveryError, NotificationError)
    assert not issubclass(PermanentDeliveryError, TransientDeliveryError)


def test_the_channel_functions_keep_their_signatures() -> None:
    import inspect

    from notifier.channels import send_email, send_sms

    assert list(inspect.signature(send_email).parameters) == ["address", "message"]
    assert list(inspect.signature(send_sms).parameters) == ["number", "message"]

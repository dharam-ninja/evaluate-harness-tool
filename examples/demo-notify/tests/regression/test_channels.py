"""Pre-existing channel behaviour. Must keep working."""

from __future__ import annotations

import pytest

from notifier import channels
from notifier.errors import PermanentDeliveryError


def test_email_rejects_a_non_address() -> None:
    with pytest.raises(PermanentDeliveryError):
        channels.send_email("nope", "hi")


def test_sms_rejects_a_non_number() -> None:
    with pytest.raises(PermanentDeliveryError):
        channels.send_sms("555", "hi")


def test_email_returns_the_transport_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(channels, "email_transport", lambda a, m: "receipt-1")
    assert channels.send_email("a@b.com", "hi") == "receipt-1"


def test_sms_returns_the_transport_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(channels, "sms_transport", lambda n, m: "receipt-2")
    assert channels.send_sms("+15550000", "hi") == "receipt-2"

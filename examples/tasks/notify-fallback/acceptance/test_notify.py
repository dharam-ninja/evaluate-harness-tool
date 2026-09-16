"""Acceptance tests for notify-fallback. Visible to the agent. Basic flow only."""

from __future__ import annotations

import pytest

from notifier import channels
from notifier.service import send_notification

RECIPIENT = {"email": "a@b.com", "phone": "+15550000"}


def test_a_successful_email_returns_its_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(channels, "email_transport", lambda a, m: "email-receipt")
    assert send_notification(RECIPIENT, "hi") == "email-receipt"


def test_sms_is_used_when_email_cannot_be_delivered(monkeypatch: pytest.MonkeyPatch) -> None:
    from notifier.errors import TransientDeliveryError

    def boom(address: str, message: str) -> str:
        raise TransientDeliveryError("provider down")

    monkeypatch.setattr(channels, "email_transport", boom)
    monkeypatch.setattr(channels, "sms_transport", lambda n, m: "sms-receipt")
    assert send_notification(RECIPIENT, "hi") == "sms-receipt"

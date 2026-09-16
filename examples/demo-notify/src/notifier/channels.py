"""Outbound channels. Each one talks to a provider and raises a delivery error."""

from __future__ import annotations

from collections.abc import Callable

from notifier.errors import PermanentDeliveryError, TransientDeliveryError
from notifier.logging_utils import get_logger

_log = get_logger(__name__)

#: Swapped out in tests. Returns a provider response id.
EmailTransport = Callable[[str, str], str]
SmsTransport = Callable[[str, str], str]


def _default_email_transport(address: str, message: str) -> str:  # pragma: no cover
    raise TransientDeliveryError("no email transport configured")


def _default_sms_transport(number: str, message: str) -> str:  # pragma: no cover
    raise TransientDeliveryError("no sms transport configured")


email_transport: EmailTransport = _default_email_transport
sms_transport: SmsTransport = _default_sms_transport


def send_email(address: str, message: str) -> str:
    """Deliver `message` to an email address. Returns the provider's receipt id."""
    if "@" not in address:
        raise PermanentDeliveryError(f"not an email address: {address!r}")
    _log.info("sending email to %s", address)
    return email_transport(address, message)


def send_sms(number: str, message: str) -> str:
    """Deliver `message` to a phone number. Returns the provider's receipt id."""
    if not number.startswith("+"):
        raise PermanentDeliveryError(f"not a phone number: {number!r}")
    _log.info("sending sms to %s", number)
    return sms_transport(number, message)

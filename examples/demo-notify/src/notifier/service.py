"""The public entry point every caller uses."""

from __future__ import annotations

from notifier.channels import send_email
from notifier.logging_utils import get_logger

_log = get_logger(__name__)


def send_notification(recipient: dict[str, str], message: str) -> str:
    """Deliver `message` to `recipient` and return the provider's receipt id.

    `recipient` carries an "email" and may carry a "phone".
    """
    _log.info("notifying %s", recipient.get("email"))
    return send_email(recipient["email"], message)

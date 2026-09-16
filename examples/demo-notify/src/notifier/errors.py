"""Delivery failures.

The split matters: a transient failure is worth trying again, a permanent one never is.
Anything that talks to a provider raises one of these two, never a bare Exception.
"""

from __future__ import annotations


class NotificationError(Exception):
    """Base class for every delivery failure."""


class TransientDeliveryError(NotificationError):
    """The provider failed in a way that may succeed on a later attempt."""


class PermanentDeliveryError(NotificationError):
    """The provider rejected the message. Trying again will not help."""

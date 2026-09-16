"""Logging conventions for this package.

Every module gets its logger from `get_logger(__name__)`. Do not call
`logging.getLogger` directly -- the prefix keeps our records separable from the
application's.
"""

from __future__ import annotations

import logging

LOG_PREFIX = "notifier"


def get_logger(name: str) -> logging.Logger:
    """Return the package logger for `name`."""
    leaf = name.rsplit(".", 1)[-1]
    return logging.getLogger(f"{LOG_PREFIX}.{leaf}")

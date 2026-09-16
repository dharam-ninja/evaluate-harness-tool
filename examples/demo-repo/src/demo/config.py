"""Settings loading for the demo billing tool."""

from __future__ import annotations

from typing import Any

DEFAULTS: dict[str, Any] = {"precision": 2, "currency": "USD", "strict": False}


class SettingsError(ValueError):
    """The settings text could not be understood."""


def load_settings(text: str) -> dict[str, Any]:
    """Parse `key=value` settings text over the top of DEFAULTS."""
    settings = dict(DEFAULTS)
    for raw in text.splitlines():
        if not raw.strip():
            continue
        if "=" not in raw:
            raise SettingsError("expected key=value, got: " + raw.strip())
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in DEFAULTS:
            raise SettingsError("unknown setting: " + key)
        if key == "precision":
            try:
                settings[key] = int(value)
            except ValueError as exc:
                raise SettingsError("precision must be a whole number") from exc
        elif key == "strict":
            if value.lower() in ("true", "yes", "1"):
                settings[key] = True
            elif value.lower() in ("false", "no", "0"):
                settings[key] = False
            else:
                raise SettingsError("strict must be a boolean")
        else:
            settings[key] = value
    return settings

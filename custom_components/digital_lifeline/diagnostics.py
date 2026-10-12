"""Diagnostics with secrets redacted."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_HOUSEHOLD, CONF_TOKEN, CONF_URL

_REDACT = {CONF_TOKEN, CONF_URL, CONF_HOUSEHOLD}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), _REDACT),
        "options": dict(entry.options),
        "watched": coordinator.watched,
        "queued_events": len(coordinator.queue),
        "last_update_success": coordinator.last_update_success,
        "last_data": coordinator.data,
    }

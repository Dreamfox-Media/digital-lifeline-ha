"""Auto-detect critical sensors in Home Assistant."""

from __future__ import annotations

import re
from typing import Iterable

from homeassistant.core import HomeAssistant

from .const import (
    CRITICAL_FIELD_KEYS,
    FIELD_BUTTON,
    FIELD_FALL,
    FIELD_SMOKE,
    FIELD_WATER,
)

_FALL_RE = re.compile(r"(^|[._\W])(fall|falling|val|valdetect\w*|fall_detect\w*)([._\W]|$)", re.I)
_BUTTON_RE = re.compile(r"(panic|sos|paniek|noodknop|nood_knop|alarm_button|emergency_button|pendant|hanger)", re.I)

# Domains the heuristics look at.
SUPPORTED_DOMAINS = ("binary_sensor", "event", "button")
# Domains accepted from portal mappings and the options flow: a `sensor.` can
# report states such as "detected" or "alarm"; `text.`/`select.` settings cannot.
MAPPABLE_DOMAINS = (*SUPPORTED_DOMAINS, "sensor")

# device_class -> portal field key (binary_sensor)
_DEVICE_CLASS_MAP = {
    "smoke": FIELD_SMOKE,
    "carbon_monoxide": FIELD_SMOKE,  # portal treats smoke/CO together
    "moisture": FIELD_WATER,
}


def classify(entity_id: str, device_class: str | None, name: str | None) -> str | None:
    """Return the portal field key for an entity, or None if it is not critical."""
    domain = entity_id.split(".", 1)[0]
    if domain not in SUPPORTED_DOMAINS:
        return None
    if domain == "binary_sensor" and device_class in _DEVICE_CLASS_MAP:
        return _DEVICE_CLASS_MAP[device_class]
    haystack = f"{entity_id} {name or ''}"
    if _BUTTON_RE.search(haystack):
        return FIELD_BUTTON
    if domain == "binary_sensor" and _FALL_RE.search(haystack):
        return FIELD_FALL
    return None


def discover(
    hass: HomeAssistant,
    mapped: Iterable[dict] | None = None,
) -> dict[str, list[str]]:
    """Return {field_key: [entity_id, ...]} from heuristics plus portal mappings."""
    result: dict[str, list[str]] = {k: [] for k in CRITICAL_FIELD_KEYS}

    for state in hass.states.async_all():
        key = classify(
            state.entity_id,
            state.attributes.get("device_class"),
            state.attributes.get("friendly_name"),
        )
        if key and state.entity_id not in result[key]:
            result[key].append(state.entity_id)

    for item in mapped or []:
        key = item.get("field_key")
        entity_id = item.get("entity_id")
        # A portal mapping can point at e.g. a settings `text.` entity; its changes
        # are not alarms, so only accept domains that can carry one.
        if (
            key in result
            and isinstance(entity_id, str)
            and entity_id.split(".", 1)[0] in MAPPABLE_DOMAINS
            and entity_id not in result[key]
        ):
            result[key].append(entity_id)

    return result


def flatten(entities: dict[str, list[str]]) -> dict[str, str]:
    """Invert to {entity_id: field_key}; first category wins on conflicts."""
    out: dict[str, str] = {}
    for key in CRITICAL_FIELD_KEYS:
        for entity_id in entities.get(key, []):
            out.setdefault(entity_id, key)
    return out

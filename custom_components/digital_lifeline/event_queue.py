"""Persistent offline queue so alarms survive portal outages and HA restarts."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, MAX_QUEUE_SIZE

_STORE_VERSION = 1


class EventQueue:
    """FIFO queue of events not yet acknowledged by the portal."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, _STORE_VERSION, f"{DOMAIN}.{entry_id}.queue")
        self._events: list[dict[str, Any]] = []

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if isinstance(data, dict) and isinstance(data.get("events"), list):
            self._events = [e for e in data["events"] if isinstance(e, dict) and e.get("event_id")]

    def _save(self) -> None:
        self._store.async_delay_save(lambda: {"events": self._events}, 1)

    def __len__(self) -> int:
        return len(self._events)

    def add(self, event: dict[str, Any]) -> None:
        self._events.append(event)
        # Drop the oldest entries first if the portal stays unreachable for very long.
        if len(self._events) > MAX_QUEUE_SIZE:
            self._events = self._events[-MAX_QUEUE_SIZE:]
        self._save()

    def peek(self, count: int) -> list[dict[str, Any]]:
        return list(self._events[:count])

    def remove(self, event_ids: set[str]) -> None:
        if not event_ids:
            return
        self._events = [e for e in self._events if e.get("event_id") not in event_ids]
        self._save()

    async def async_flush_to_disk(self) -> None:
        await self._store.async_save({"events": self._events})

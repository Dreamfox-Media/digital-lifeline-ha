"""Coordinator: heartbeat, state-change listener and offline-safe event delivery."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, __version__ as HA_VERSION
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import (
    LifelineAuthError,
    LifelineClient,
    LifelineConnectionError,
    LifelineDisabledError,
    LifelineRequestError,
)
from .const import (
    DEBOUNCE_S,
    DOMAIN,
    EVENT_INCIDENT,
    FIELD_FALL,
    HEARTBEAT_INTERVAL_S,
    INTEGRATION_VERSION,
    ISSUE_DISABLED,
    RETRY_BACKOFF_S,
    SEND_BATCH_SIZE,
    TEST_ENTITY_ID,
)
from .event_queue import EventQueue

_LOGGER = logging.getLogger(__name__)
_BAD = (STATE_UNAVAILABLE, STATE_UNKNOWN)


class LifelineCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Owns the portal connection for one config entry."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: LifelineClient,
        queue: EventQueue,
        watched: dict[str, str],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=HEARTBEAT_INTERVAL_S),
        )
        self.client = client
        self.queue = queue
        self.watched = watched  # entity_id -> portal field_key
        self._flush_lock = asyncio.Lock()
        self._last_on: dict[str, datetime] = {}
        self._retry_step = 0
        self._cancel_retry: CALLBACK_TYPE | None = None
        self._incident_signature: tuple[tuple[str, str], ...] = ()

    # -- helpers ---------------------------------------------------------------

    def _name_for(self, entity_id: str) -> str | None:
        state = self.hass.states.get(entity_id)
        return state.attributes.get("friendly_name") if state else None

    def _heartbeat_payload(self) -> dict[str, Any]:
        watched = []
        unavailable = []
        for entity_id, field_key in self.watched.items():
            state = self.hass.states.get(entity_id)
            item: dict[str, Any] = {
                "entity_id": entity_id,
                "field_key": field_key,
                "name": self._name_for(entity_id),
            }
            watched.append(item)
            if state is None or state.state in _BAD:
                unavailable.append(dict(item))
            elif isinstance(state.attributes.get("battery_level"), (int, float)):
                battery = state.attributes["battery_level"]
                if battery <= 10:
                    unavailable.append({**item, "battery": battery})
        return {
            "integration_version": INTEGRATION_VERSION,
            "ha_version": HA_VERSION,
            "watched_entities": watched,
            "unavailable_entities": unavailable,
        }

    def _new_event(
        self,
        entity_id: str,
        field_key: str,
        state: str,
        observed_at: datetime,
        test: bool = False,
    ) -> dict[str, Any]:
        return {
            "event_id": uuid.uuid4().hex,
            "field_key": field_key,
            "entity_id": entity_id,
            "state": state,
            "observed_at": observed_at.astimezone(timezone.utc).isoformat(),
            "friendly_name": self._name_for(entity_id),
            "test": test,
        }

    # -- state changes -----------------------------------------------------------

    @callback
    def async_handle_state_change(self, event: Event) -> None:
        """Called for every state change of a watched entity."""
        new = event.data.get("new_state")
        old = event.data.get("old_state")
        entity_id: str = event.data["entity_id"]
        field_key = self.watched.get(entity_id)
        if new is None or field_key is None or new.state in _BAD:
            return

        domain = entity_id.split(".", 1)[0]
        if domain in ("event", "button"):
            # Every new press/trigger changes the entity state (timestamp).
            if old is None or old.state in _BAD or old.state == new.state:
                return
            state = "pressed"
        else:
            if old is not None and old.state == new.state:
                return
            state = new.state

        now = datetime.now(timezone.utc)
        if state in ("on", "pressed"):
            last = self._last_on.get(entity_id)
            if last and (now - last).total_seconds() < DEBOUNCE_S:
                return
            self._last_on[entity_id] = now

        self.queue.add(self._new_event(entity_id, field_key, state, new.last_changed))
        self.hass.async_create_task(self.async_flush_queue(), eager_start=True)

    # -- delivery ----------------------------------------------------------------

    async def async_flush_queue(self) -> None:
        """Send queued events; on failure keep them and retry with back-off."""
        if self._flush_lock.locked():
            return
        async with self._flush_lock:
            try:
                while len(self.queue):
                    batch = self.queue.peek(SEND_BATCH_SIZE)
                    response = await self.client.send_events(batch)
                    acked = {
                        r.get("event_id")
                        for r in response.get("results", [])
                        if isinstance(r, dict) and r.get("event_id")
                    }
                    if not acked:
                        raise LifelineConnectionError("portal acknowledged nothing")
                    self.queue.remove(acked)
                self._retry_step = 0
            except LifelineAuthError:
                self.config_entry.async_start_reauth(self.hass)
            except LifelineDisabledError:
                self._raise_disabled_issue()
                self._schedule_retry()
            except LifelineRequestError as err:
                # Portal says the batch is invalid; drop it so it cannot block the queue.
                _LOGGER.error("Portal rejected events, dropping batch: %s", err)
                self.queue.remove({e["event_id"] for e in self.queue.peek(SEND_BATCH_SIZE)})
            except LifelineConnectionError as err:
                _LOGGER.warning("Portal unreachable, %d event(s) queued: %s", len(self.queue), err)
                self._schedule_retry()

    @callback
    def _schedule_retry(self) -> None:
        if self._cancel_retry is not None:
            return
        delay = RETRY_BACKOFF_S[min(self._retry_step, len(RETRY_BACKOFF_S) - 1)]
        self._retry_step += 1

        async def _retry(_now: datetime) -> None:
            self._cancel_retry = None
            await self.async_flush_queue()

        self._cancel_retry = async_call_later(self.hass, delay, _retry)

    @callback
    def async_shutdown_retry(self) -> None:
        if self._cancel_retry is not None:
            self._cancel_retry()
            self._cancel_retry = None

    def _raise_disabled_issue(self) -> None:
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            ISSUE_DISABLED,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=ISSUE_DISABLED,
        )

    # -- heartbeat ---------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if len(self.queue):
                await self.async_flush_queue()
            data = await self.client.heartbeat(self._heartbeat_payload())
        except LifelineAuthError as err:
            raise ConfigEntryAuthFailed("Token rejected by the portal") from err
        except LifelineDisabledError as err:
            self._raise_disabled_issue()
            raise UpdateFailed("Home Assistant app is switched off in the portal") from err
        except (LifelineConnectionError, LifelineRequestError) as err:
            raise UpdateFailed(str(err)) from err

        ir.async_delete_issue(self.hass, DOMAIN, ISSUE_DISABLED)
        self._publish_incidents(data.get("open_incidents") or [])
        if data.get("test_requested"):
            await self.async_send_test()
        return data

    def _publish_incidents(self, incidents: list[dict[str, Any]]) -> None:
        signature = tuple(sorted((str(i.get("id")), str(i.get("status"))) for i in incidents))
        if signature == self._incident_signature:
            return
        self._incident_signature = signature
        self.hass.bus.async_fire(EVENT_INCIDENT, {"incidents": incidents})

    async def async_send_test(self) -> None:
        """Send a flagged test event through the full delivery path."""
        event = self._new_event(TEST_ENTITY_ID, FIELD_FALL, "on", datetime.now(timezone.utc), test=True)
        self.queue.add(event)
        await self.async_flush_queue()

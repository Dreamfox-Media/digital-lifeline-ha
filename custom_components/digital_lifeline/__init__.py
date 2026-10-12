"""Digital Lifeline: push critical Home Assistant sensors to the Lifeline portal."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event

from .client import LifelineClient, parse_webhook_url
from .const import (
    CONF_ENTITIES,
    CONF_HOUSEHOLD,
    CONF_MAPPED,
    CONF_TOKEN,
    CONF_URL,
    DOMAIN,
    SERVICE_SEND_TEST,
)
from .coordinator import LifelineCoordinator
from .discovery import discover, flatten
from .event_queue import EventQueue

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]

type LifelineConfigEntry = ConfigEntry[LifelineCoordinator]


def _selected_entities(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, str]:
    """Options win; otherwise heuristics plus the sensors already mapped in the portal."""
    chosen: dict[str, list[str]] | None = entry.options.get(CONF_ENTITIES)
    if chosen is None:
        chosen = discover(hass, entry.data.get(CONF_MAPPED))
    return flatten(chosen)


async def async_setup_entry(hass: HomeAssistant, entry: LifelineConfigEntry) -> bool:
    base, household = parse_webhook_url(entry.data[CONF_URL])
    client = LifelineClient(async_get_clientsession(hass), base, household, entry.data[CONF_TOKEN])

    queue = EventQueue(hass, entry.entry_id)
    await queue.async_load()

    watched = _selected_entities(hass, entry)
    coordinator = LifelineCoordinator(hass, entry, client, queue, watched)

    # First heartbeat: raises ConfigEntryAuthFailed / ConfigEntryNotReady for us.
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    if watched:
        entry.async_on_unload(
            async_track_state_change_event(hass, list(watched), coordinator.async_handle_state_change)
        )
    else:
        _LOGGER.warning("No critical sensors detected; select them in the integration options")

    async def _on_stop(_event: Any) -> None:
        await queue.async_flush_to_disk()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _on_stop))
    entry.async_on_unload(coordinator.async_shutdown_retry)
    entry.async_on_unload(entry.add_update_listener(_async_reload))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_TEST):

        async def _send_test(_call: ServiceCall) -> None:
            entries = hass.config_entries.async_loaded_entries(DOMAIN)
            if not entries:
                raise ServiceValidationError("Digital Lifeline is not set up")
            for loaded in entries:
                await loaded.runtime_data.async_send_test()

        hass.services.async_register(DOMAIN, SERVICE_SEND_TEST, _send_test)

    # Anything queued while HA was down goes out now.
    hass.async_create_task(coordinator.async_flush_queue())
    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: LifelineConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and not hass.config_entries.async_loaded_entries(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_SEND_TEST)
    return unloaded

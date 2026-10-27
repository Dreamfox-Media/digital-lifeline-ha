"""Connection and incident binary sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, INTEGRATION_VERSION
from .coordinator import LifelineCoordinator


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: LifelineCoordinator = entry.runtime_data
    async_add_entities([LifelineConnectionSensor(coordinator, entry), LifelineIncidentSensor(coordinator, entry)])


_OBJECT_IDS = {"connection": "portal_connection", "incident": "open_incident"}


class _Base(CoordinatorEntity[LifelineCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: LifelineCoordinator, entry, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        # Keep entity ids stable (digital_lifeline_*) regardless of the display name.
        self.entity_id = f"binary_sensor.digital_lifeline_{_OBJECT_IDS[key]}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Digilifeline",
            manufacturer="Digilifeline",
            sw_version=INTEGRATION_VERSION,
        )


class LifelineConnectionSensor(_Base):
    """On while the portal answers the heartbeat (this drives the green check in the portal)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: LifelineCoordinator, entry) -> None:
        super().__init__(coordinator, entry, "connection")

    @property
    def available(self) -> bool:
        return True  # an unreachable portal is the information, not "unavailable"

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"queued_events": len(self.coordinator.queue)}


class LifelineIncidentSensor(_Base):
    """On while the portal has an open incident for this household."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: LifelineCoordinator, entry) -> None:
        super().__init__(coordinator, entry, "incident")

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        return bool(self.coordinator.data.get("open_incidents"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        incidents = (self.coordinator.data or {}).get("open_incidents") or []
        return {"incidents": incidents}

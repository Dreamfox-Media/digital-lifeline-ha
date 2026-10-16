"""Integration tests with a mocked portal."""

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.digital_lifeline.client import LifelineAuthError, LifelineConnectionError
from custom_components.digital_lifeline.const import DOMAIN, EVENT_INCIDENT

URL = "https://portal.example/api/public/webhooks/ha-integration?household=hh-1"
HB = {"ok": True, "test_requested": False, "open_incidents": []}
CLIENT = "custom_components.digital_lifeline.client.LifelineClient"


def _ack(events):
    return {"ok": True, "results": [{"event_id": e["event_id"], "result": "processed"} for e in events]}


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="hh-1",
        data={"url": URL, "token": "tok", "household": "hh-1", "mapped_entities": []},
    )


@contextmanager
def _portal(heartbeat=HB, send=None):
    send = send or AsyncMock(side_effect=_ack)
    with patch(f"{CLIENT}.heartbeat", AsyncMock(return_value=heartbeat)), patch(f"{CLIENT}.send_events", send):
        yield send


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_alarm_is_pushed_immediately(hass: HomeAssistant):
    hass.states.async_set("binary_sensor.bedroom_fall", "off", {"friendly_name": "Bedroom fall detected"})
    entry = _entry()
    with _portal() as send:
        await _setup(hass, entry)
        hass.states.async_set("binary_sensor.bedroom_fall", "on", {"friendly_name": "Bedroom fall detected"})
        await hass.async_block_till_done()

        assert send.await_count == 1
        event = send.await_args.args[0][0]
        assert event["field_key"] == "val_detectie"
        assert event["entity_id"] == "binary_sensor.bedroom_fall"
        assert event["state"] == "on"
        assert event["test"] is False
        assert len(entry.runtime_data.queue) == 0


async def test_portal_down_keeps_event_queued_then_delivers(hass: HomeAssistant):
    hass.states.async_set("binary_sensor.smoke_kitchen", "off", {"device_class": "smoke"})
    entry = _entry()
    failing = AsyncMock(side_effect=LifelineConnectionError("down"))
    with _portal(send=failing):
        await _setup(hass, entry)
        hass.states.async_set("binary_sensor.smoke_kitchen", "on", {"device_class": "smoke"})
        await hass.async_block_till_done()
        assert len(entry.runtime_data.queue) == 1  # kept, not lost

        failing.side_effect = _ack
        await entry.runtime_data.async_flush_queue()
        assert len(entry.runtime_data.queue) == 0


async def test_debounce_ignores_repeated_on(hass: HomeAssistant):
    hass.states.async_set("binary_sensor.panic_button", "off")
    entry = _entry()
    with _portal() as send:
        await _setup(hass, entry)
        for state in ("on", "off", "on"):
            hass.states.async_set("binary_sensor.panic_button", state)
            await hass.async_block_till_done()
        sent_states = [e["state"] for call in send.await_args_list for e in call.args[0]]
        assert sent_states.count("on") == 1


async def test_heartbeat_test_request_sends_flagged_event(hass: HomeAssistant):
    entry = _entry()
    with _portal(heartbeat={**HB, "test_requested": True}) as send:
        await _setup(hass, entry)
        flagged = [e for call in send.await_args_list for e in call.args[0] if e["test"]]
        assert len(flagged) == 1


async def test_incident_change_fires_bus_event(hass: HomeAssistant):
    events = async_capture_events(hass, EVENT_INCIDENT)
    entry = _entry()
    incident = {"id": "i1", "category": "valdetectie", "status": "open", "opened_at": "x", "responder": None}
    with _portal(heartbeat={**HB, "open_incidents": [incident]}):
        await _setup(hass, entry)
        assert len(events) == 1
        assert events[0].data["incidents"][0]["id"] == "i1"
        state = hass.states.get("binary_sensor.digital_lifeline_open_incident")
        assert state is not None
        assert state.state == "on"


async def test_auth_failure_ends_in_setup_error(hass: HomeAssistant):
    entry = _entry()
    entry.add_to_hass(hass)
    with patch(f"{CLIENT}.heartbeat", AsyncMock(side_effect=LifelineAuthError("x"))):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_client_retries_temporary_errors_but_rejects_invalid(hass: HomeAssistant, aioclient_mock):
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from custom_components.digital_lifeline.client import LifelineClient, LifelineRequestError

    base = "https://portal.example/api/public/webhooks/ha-integration"
    client = LifelineClient(async_get_clientsession(hass), base, "hh-1", "tok")
    for status in (404, 408, 429, 503):
        aioclient_mock.clear_requests()
        aioclient_mock.post(f"{base}/event", status=status, json={})
        try:
            await client.send_events([{"event_id": "e1"}])
        except LifelineConnectionError:
            pass
        else:
            raise AssertionError(f"status {status} should be retryable")
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{base}/event", status=400, json={"error": "events required"})
    try:
        await client.send_events([])
    except LifelineRequestError:
        pass
    else:
        raise AssertionError("status 400 should not be retryable")


async def test_discover_ignores_mapped_entities_that_cannot_alarm(hass: HomeAssistant):
    from custom_components.digital_lifeline.discovery import discover

    found = discover(
        hass,
        [
            {"field_key": "val_detectie", "entity_id": "text.val_detectie_fall_detection_settings"},
            {"field_key": "val_detectie", "entity_id": "binary_sensor.radar_fall"},
            {"field_key": "val_detectie", "entity_id": "sensor.radar_fall_status"},
        ],
    )
    assert found["val_detectie"] == ["binary_sensor.radar_fall", "sensor.radar_fall_status"]

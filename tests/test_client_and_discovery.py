"""Pure-logic tests: URL parsing and sensor classification."""

import pytest

from custom_components.digital_lifeline.client import parse_webhook_url
from custom_components.digital_lifeline.discovery import classify, flatten


def test_parse_webhook_url_ok():
    base, hh = parse_webhook_url("https://my.example.com/api/public/webhooks/ha-integration/?household=abc-123")
    assert base == "https://my.example.com/api/public/webhooks/ha-integration"
    assert hh == "abc-123"


@pytest.mark.parametrize(
    "bad",
    ["", "not a url", "ftp://x/y?household=1", "https://x/api?nohousehold=1", "https:///path?household=1"],
)
def test_parse_webhook_url_invalid(bad):
    with pytest.raises(ValueError):
        parse_webhook_url(bad)


@pytest.mark.parametrize(
    ("entity_id", "device_class", "name", "expected"),
    [
        ("binary_sensor.kitchen_smoke", "smoke", "Kitchen smoke", "rookmelder"),
        ("binary_sensor.hall_co", "carbon_monoxide", None, "rookmelder"),
        ("binary_sensor.cellar_leak", "moisture", None, "waterlek"),
        ("binary_sensor.bedroom_fall_detected", None, "Bedroom fall detected", "val_detectie"),
        ("binary_sensor.valdetectie_slaapkamer", None, "Valdetectie slaapkamer", "val_detectie"),
        ("event.panic_button_action", None, "Panic button", "noodknop"),
        ("binary_sensor.noodknop_woonkamer", None, None, "noodknop"),
        ("binary_sensor.front_door", "door", "Front door", None),
        ("binary_sensor.valve_state", None, "Valve", None),
        ("sensor.temperature", "temperature", None, None),
    ],
)
def test_classify(entity_id, device_class, name, expected):
    assert classify(entity_id, device_class, name) == expected


def test_flatten_first_category_wins():
    flat = flatten({"val_detectie": ["binary_sensor.a"], "noodknop": ["binary_sensor.a", "event.b"]})
    assert flat == {"binary_sensor.a": "val_detectie", "event.b": "noodknop"}

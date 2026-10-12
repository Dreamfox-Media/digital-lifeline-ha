"""Constants for the Digital Lifeline integration."""

from __future__ import annotations

DOMAIN = "digital_lifeline"
INTEGRATION_VERSION = "0.1.0"

CONF_URL = "url"
CONF_TOKEN = "token"
CONF_HOUSEHOLD = "household"
CONF_MAPPED = "mapped_entities"
CONF_ENTITIES = "entities"

HEARTBEAT_INTERVAL_S = 60
REQUEST_TIMEOUT_S = 10
SEND_BATCH_SIZE = 20
MAX_QUEUE_SIZE = 500
# Ignore a repeated "on" for the same entity within this window (seconds).
DEBOUNCE_S = 5
# Back-off steps (seconds) for re-sending queued events after a failure.
RETRY_BACKOFF_S = (2, 5, 10, 30, 60)

# Portal field keys that are treated as critical (immediate emergency).
FIELD_FALL = "val_detectie"
FIELD_BUTTON = "noodknop"
FIELD_SMOKE = "rookmelder"
FIELD_WATER = "waterlek"
CRITICAL_FIELD_KEYS = (FIELD_FALL, FIELD_BUTTON, FIELD_SMOKE, FIELD_WATER)

EVENT_INCIDENT = f"{DOMAIN}_incident"
SERVICE_SEND_TEST = "send_test_event"

ISSUE_DISABLED = "integration_disabled"
ISSUE_UNREACHABLE = "portal_unreachable"

TEST_ENTITY_ID = "digital_lifeline.test"

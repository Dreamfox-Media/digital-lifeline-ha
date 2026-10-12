"""Config flow for Digital Lifeline."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import (
    LifelineAuthError,
    LifelineClient,
    LifelineConnectionError,
    LifelineDisabledError,
    LifelineError,
    parse_webhook_url,
)
from .const import (
    CONF_ENTITIES,
    CONF_HOUSEHOLD,
    CONF_MAPPED,
    CONF_TOKEN,
    CONF_URL,
    CRITICAL_FIELD_KEYS,
    DOMAIN,
    INTEGRATION_VERSION,
)
from .discovery import discover

_LOGGER = logging.getLogger(__name__)


async def _validate(hass, url: str, token: str) -> tuple[str, list[dict[str, Any]]]:
    """Handshake with the portal. Returns (household_id, mapped_entities)."""
    base, household = parse_webhook_url(url)
    client = LifelineClient(async_get_clientsession(hass), base, household, token.strip())
    result = await client.handshake(
        {"integration_version": INTEGRATION_VERSION, "ha_version": HA_VERSION}
    )
    return household, list(result.get("mapped_entities") or [])


def _error_key(err: Exception) -> str:
    if isinstance(err, ValueError):
        return "invalid_url"
    if isinstance(err, LifelineAuthError):
        return "invalid_auth"
    if isinstance(err, LifelineDisabledError):
        return "integration_disabled"
    if isinstance(err, LifelineConnectionError):
        return "cannot_connect"
    return "unknown"


class DigitalLifelineConfigFlow(ConfigFlow, domain=DOMAIN):
    """Paste webhook URL + token from the portal."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                household, mapped = await _validate(self.hass, user_input[CONF_URL], user_input[CONF_TOKEN])
            except (ValueError, LifelineError) as err:
                errors["base"] = _error_key(err)
            else:
                await self.async_set_unique_id(household)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Digital Lifeline",
                    data={
                        CONF_URL: user_input[CONF_URL].strip(),
                        CONF_TOKEN: user_input[CONF_TOKEN].strip(),
                        CONF_HOUSEHOLD: household,
                        CONF_MAPPED: mapped,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_URL): selector.TextSelector(),
                vol.Required(CONF_TOKEN): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            try:
                await _validate(self.hass, entry.data[CONF_URL], user_input[CONF_TOKEN])
            except (ValueError, LifelineError) as err:
                errors["base"] = _error_key(err)
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_TOKEN: user_input[CONF_TOKEN].strip()}
                )
        schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                )
            }
        )
        return self.async_show_form(step_id="reauth_confirm", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return DigitalLifelineOptionsFlow()


class DigitalLifelineOptionsFlow(OptionsFlow):
    """Choose which entities count as fall / button / smoke / water sensors."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={CONF_ENTITIES: {k: list(user_input.get(k, [])) for k in CRITICAL_FIELD_KEYS}})

        current = self.config_entry.options.get(CONF_ENTITIES)
        if current is None:
            current = discover(self.hass, self.config_entry.data.get(CONF_MAPPED))

        entity_selector = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "event", "button"], multiple=True)
        )
        schema = vol.Schema(
            {
                vol.Optional(key, default=current.get(key, [])): entity_selector
                for key in CRITICAL_FIELD_KEYS
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

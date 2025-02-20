"""Config flow for the storj integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import instance_id

from .api import StorjClient
from .exceptions import InvalidAuth, CannotConnect
from .const import CONF_ACCESS_GRANT, CONF_BUCKET_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCESS_GRANT): str,
        vol.Required(CONF_BUCKET_NAME): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.
    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    client = StorjClient(await instance_id.async_get(hass), data[CONF_BUCKET_NAME])

    if not await client.authenticate(data[CONF_ACCESS_GRANT]):
        raise InvalidAuth
    elif not await client.satelitte_is_live():
        raise CannotConnect("Satelitte is not reachable")

    # Return info that you want to store in the config entry.
    return {"title": "Storj"}


class StorjConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for storj."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
                return self.async_abort(reason="unknown")
            else:
                await self.async_set_unique_id(user_input[CONF_ACCESS_GRANT])
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

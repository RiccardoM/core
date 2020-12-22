"""Config flow for IdealService Waste integration."""
from typing import Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

from .client import Client
from .const import CONF_CALENDAR_ID, CONF_PLACE_ID, DOMAIN, LOGGER

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLACE_ID): str,
        vol.Required(CONF_CALENDAR_ID): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IdealService Waste."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Define the config flow to handle options."""
        return IdealServiceWasteOptionsFlowHandler(config_entry)

    async def async_step_import(self, import_config: dict = None) -> dict:
        """Handle configuration via YAML import."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input: dict = None) -> dict:
        """Handle configuration via the UI."""
        if user_input is None:
            # We do not have any input from the user, so build a form to allow them to input the config
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA,
                errors={},
            )

        # Build an entity unique id
        unique_id = f"{user_input[CONF_PLACE_ID]}, {user_input[CONF_CALENDAR_ID]}"

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        # Verify both the zone and calendar ids
        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            client = Client(
                user_input[CONF_PLACE_ID], user_input[CONF_CALENDAR_ID], session=session
            )
            await client.async_get_next_pickup_event()
        except Exception as err:
            LOGGER.error("Error during setup of integration: %s", err)
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA,
                errors={"base": "invalid_place_id_or_calendar_id"},
            )

        # Build the entity
        return self.async_create_entry(
            title=unique_id,
            data={
                CONF_PLACE_ID: user_input[CONF_PLACE_ID],
                CONF_CALENDAR_ID: user_input[CONF_CALENDAR_ID],
            },
        )


class IdealServiceWasteOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a IdealService Waste options flow."""

    def __init__(self, entry: config_entries.ConfigEntry):
        """Initialize."""
        self._entry = entry

    async def async_step_init(self, user_input: Optional[dict] = None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init")

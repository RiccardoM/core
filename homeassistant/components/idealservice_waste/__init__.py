"""The idealservice integration."""
import asyncio
from datetime import timedelta
from typing import List

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import Client, PickupEvent
from .const import (
    CONF_CALENDAR_ID,
    CONF_PLACE_ID,
    DATA_COORDINATOR,
    DATA_LISTENER,
    DOMAIN,
    LOGGER,
)
from .errors import IdealServiceError

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

DEFAULT_UPDATE_INTERVAL = timedelta(days=1)
PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the IdealService Waste component."""
    hass.data[DOMAIN] = {DATA_COORDINATOR: {}, DATA_LISTENER: {}}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up IdealService as config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    client = Client(
        entry.data[CONF_PLACE_ID], entry.data[CONF_CALENDAR_ID], session=session
    )

    async def async_get_pickup_events() -> List[PickupEvent]:
        """Get the next pickup."""
        try:
            return await client.async_get_pickup_events(days=28, offset=0)
        except IdealServiceError as err:
            raise UpdateFailed(
                f"Error while requesting data from IdealService: {err}"
            ) from err

    coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name=f"Place {entry.data[CONF_PLACE_ID]}, Calendar {entry.data[CONF_CALENDAR_ID]}",
        update_interval=DEFAULT_UPDATE_INTERVAL,
        update_method=async_get_pickup_events,
    )

    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][DATA_COORDINATOR][entry.entry_id] = coordinator

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    hass.data[DOMAIN][DATA_LISTENER][entry.entry_id] = entry.add_update_listener(
        async_reload_entry
    )

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle an options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an IdealService config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN][DATA_COORDINATOR].pop(entry.entry_id)
        cancel_listener = hass.data[DOMAIN][DATA_LISTENER].pop(entry.entry_id)
        cancel_listener()

    return unload_ok

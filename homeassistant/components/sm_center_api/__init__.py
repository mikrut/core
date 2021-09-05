"""The sm_center_api integration."""
from __future__ import annotations

import aiohttp
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .config_flow import PlaceholderHub


def get_api(hass: HomeAssistant, entry: ConfigEntry) -> PlaceholderHub:
    return hass.data[DOMAIN][entry.entry_id]


def set_api(hass: HomeAssistant, entry: ConfigEntry, api: PlaceholderHub):
    hass.data[DOMAIN][entry.entry_id] = api


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up sm_center_api from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api = PlaceholderHub.from_config(
        websession=aiohttp.ClientSession(), config=entry.data["api"]
    )
    set_api(hass, entry, api)

    async def handler(call: ServiceCall):
        """Handle the measurement service call."""
        measurement = call.data["measurement"]
        factory_number = call.data["factory_number"]
        units = call.data["units"]
        meters = await api.meters_list()
        meter_to_report = None
        for meter in meters:
            if meter.factory_number == factory_number and meter.units == units:
                meter_to_report = meter
                break
        if meter_to_report is None:
            raise Exception("Meter not found")
        await api.meters_save_value(meter_to_report, measurement)

    hass.services.async_register(
        DOMAIN,
        "measurement",
        handler,
        schema=vol.Schema(
            {
                vol.Required("measurement"): cv.positive_float,
                vol.Required("factory_number"): str,
                vol.Required("units"): str,
            }
        ),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await get_api(hass, entry).unload()
    return True

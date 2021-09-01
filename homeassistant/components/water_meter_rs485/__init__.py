"""The Water Meter RS485 integration."""
from __future__ import annotations

from homeassistant.components.sensor import DOMAIN as SENSOR
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LENGTH
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .rs485.master import Master as RS485Master

PLATFORMS = [
    SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Water Meter RS485 from a config entry."""
    rs485 = RS485Master(entry.data)
    await hass.async_add_executor_job(rs485.open)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = {
        "master": rs485,
    }
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    rs485 = hass.data[DOMAIN][entry.entry_id]
    await hass.async_add_executor_job(rs485.close, rs485)

    return unload_ok

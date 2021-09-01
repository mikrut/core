"""The Water Meter RS485 integration."""
from __future__ import annotations

from decimal import Decimal
from os import stat
from typing import SupportsIndex

import serial

from homeassistant.components.sensor import DOMAIN as SENSOR
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LENGTH
from homeassistant.core import HomeAssistant
import threading
from .protocol import (
    ReadVolumeRequest,
    ReadVolumeResponse,
)

from .const import (
    CONF_BAUDRATE,
    CONF_BYTE_SIZE,
    CONF_PARITY,
    CONF_SERIAL_PORT,
    CONF_STOP_BITS,
    DOMAIN,
    ByteSizeType,
    ParityType,
    StopBitsType,
)

PLATFORMS = [
    SENSOR,
]


class RS485Master:
    def __init__(self, config):
        self._serial_port = serial.Serial(
            port=None,
            baudrate=config[CONF_BAUDRATE],
            bytesize=ByteSizeType.get_by_description(config[CONF_BYTE_SIZE]),
            parity=ParityType.get_by_description(config[CONF_PARITY]),
            stopbits=StopBitsType.get_by_description(config[CONF_STOP_BITS]),
        )
        self._serial_port.port = config[CONF_SERIAL_PORT]
        self._serial_port.timeout = 2
        self._lock = threading.Lock()

    def open(self):
        self._serial_port.open()

    def read_value(self, unique_id: str) -> Decimal | None:
        with self._lock:
            sensor_id = int(unique_id)

            read_request = ReadVolumeRequest(address=sensor_id)
            self._serial_port.write(read_request.frame)

            response_frame = self._serial_port.read(
                ReadVolumeResponse.EXPECTED_TOTAL_LENGTH
            )
            if len(response_frame) < ReadVolumeResponse.EXPECTED_TOTAL_LENGTH:
                return None

            response = ReadVolumeResponse(response_frame)
            assert response.address == sensor_id
            assert response.id == read_request.id
            return response.volume


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

"""The Water Meter RS485 integration."""
from __future__ import annotations

from decimal import Decimal

import libscrc
import serial

from homeassistant.components.sensor import DOMAIN as SENSOR
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LENGTH
from homeassistant.core import HomeAssistant

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

    def open(self):
        self._serial_port.open()

    def read_value(self, unique_id: str) -> Decimal | None:
        sensor_id = int(unique_id)
        address = 0
        digit_coeff = 0
        while sensor_id > 0:
            last_digit = sensor_id % 10
            sensor_id //= 10
            address |= last_digit << digit_coeff
            digit_coeff += 4

        message = bytearray()
        ADDRESS_SIZE_BYTES = 4
        for i in range(0, ADDRESS_SIZE_BYTES):
            message.append((address >> (ADDRESS_SIZE_BYTES - i - 1) * 8) & 0xFF)

        COMMAND_READ_VOLUME = 0x01
        command = COMMAND_READ_VOLUME
        message.append(command)

        LENGTH_BYTE_INDEX = 5
        message.append(0x00)

        message.append(0x01)
        message.append(0x00)
        message.append(0x00)
        message.append(0x00)

        message.append(0xFD)
        message.append(0xEC)

        length = len(message) + 2
        message[LENGTH_BYTE_INDEX] = length

        crc16 = libscrc.modbus(message)
        message.append((crc16 >> 0) & 0xFF)
        message.append((crc16 >> 8) & 0xFF)

        self._serial_port.write(message)
        response = self._serial_port.read(length)

        volume_data = response[6:10]
        volume = Decimal(int.from_bytes(volume_data, "little"))
        volume /= 1000

        return volume


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

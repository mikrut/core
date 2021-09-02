"""Config flow for Water Meter RS485 integration."""
from __future__ import annotations

import logging
import os
from typing import Any

import serial.tools.list_ports
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_SERIAL_PORT, CONF_WATERMETER_RS485_PORT_SCHEMA, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Water Meter RS485."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        list_of_ports = [
            f"{p}, s/n: {p.serial_number or 'n/a'}"
            + (f" - {p.manufacturer}" if p.manufacturer else "")
            for p in ports
        ]

        if not list_of_ports:
            return self.async_abort(reason="no_serial_port")

        if user_input is not None:
            user_selection = user_input[CONF_SERIAL_PORT]

            port = ports[list_of_ports.index(user_selection)]
            dev_path = await self.hass.async_add_executor_job(
                get_serial_by_id, port.device
            )
            user_input[CONF_SERIAL_PORT] = dev_path

            return self.async_create_entry(
                title=user_selection,
                data=user_input,
            )

        schema = CONF_WATERMETER_RS485_PORT_SCHEMA
        schema = schema.extend(
            schema={vol.Required(CONF_SERIAL_PORT): vol.In(list_of_ports)}
        )
        return self.async_show_form(step_id="user", data_schema=schema)


def get_serial_by_id(dev_path: str) -> str:
    """Return a /dev/serial/by-id match for given device if available."""
    by_id = "/dev/serial/by-id"
    if not os.path.isdir(by_id):
        return dev_path

    for path in (entry.path for entry in os.scandir(by_id) if entry.is_symlink()):
        if os.path.realpath(path) == dev_path:
            return path
    return dev_path

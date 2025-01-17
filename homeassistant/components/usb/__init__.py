"""The USB Discovery integration."""
from __future__ import annotations

import dataclasses
import logging
import os
import sys

from serial.tools.list_ports import comports
from serial.tools.list_ports_common import ListPortInfo
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import system_info
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_usb

from .const import DOMAIN
from .flow import FlowDispatcher, USBFlow
from .models import USBDevice
from .utils import usb_device_from_port

_LOGGER = logging.getLogger(__name__)

REQUEST_SCAN_COOLDOWN = 60  # 1 minute cooldown


def human_readable_device_name(
    device: str,
    serial_number: str | None,
    manufacturer: str | None,
    description: str | None,
    vid: str | None,
    pid: str | None,
) -> str:
    """Return a human readable name from USBDevice attributes."""
    device_details = f"{device}, s/n: {serial_number or 'n/a'}"
    manufacturer_details = f" - {manufacturer}" if manufacturer else ""
    vendor_details = f" - {vid}:{pid}" if vid else ""
    full_details = f"{device_details}{manufacturer_details}{vendor_details}"

    if not description:
        return full_details
    return f"{description[:26]} - {full_details}"


def get_serial_by_id(dev_path: str) -> str:
    """Return a /dev/serial/by-id match for given device if available."""
    by_id = "/dev/serial/by-id"
    if not os.path.isdir(by_id):
        return dev_path

    for path in (entry.path for entry in os.scandir(by_id) if entry.is_symlink()):
        if os.path.realpath(path) == dev_path:
            return path
    return dev_path


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the USB Discovery integration."""
    usb = await async_get_usb(hass)
    usb_discovery = USBDiscovery(hass, FlowDispatcher(hass), usb)
    await usb_discovery.async_setup()
    hass.data[DOMAIN] = usb_discovery
    websocket_api.async_register_command(hass, websocket_usb_scan)

    return True


class USBDiscovery:
    """Manage USB Discovery."""

    def __init__(
        self,
        hass: HomeAssistant,
        flow_dispatcher: FlowDispatcher,
        usb: list[dict[str, str]],
    ) -> None:
        """Init USB Discovery."""
        self.hass = hass
        self.flow_dispatcher = flow_dispatcher
        self.usb = usb
        self.seen: set[tuple[str, ...]] = set()
        self.observer_active = False
        self._request_debouncer: Debouncer | None = None

    async def async_setup(self) -> None:
        """Set up USB Discovery."""
        await self._async_start_monitor()
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self.async_start)

    async def async_start(self, event: Event) -> None:
        """Start USB Discovery and run a manual scan."""
        self.flow_dispatcher.async_start()
        await self._async_scan_serial()

    async def _async_start_monitor(self) -> None:
        """Start monitoring hardware with pyudev."""
        if not sys.platform.startswith("linux"):
            return
        info = await system_info.async_get_system_info(self.hass)
        if info.get("docker") and not info.get("hassio"):
            return

        from pyudev import (  # pylint: disable=import-outside-toplevel
            Context,
            Monitor,
            MonitorObserver,
        )

        try:
            context = Context()
        except (ImportError, OSError):
            return

        monitor = Monitor.from_netlink(context)
        monitor.filter_by(subsystem="tty")
        observer = MonitorObserver(
            monitor, callback=self._device_discovered, name="usb-observer"
        )
        observer.start()
        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, lambda event: observer.stop()
        )
        self.observer_active = True

    def _device_discovered(self, device):
        """Call when the observer discovers a new usb tty device."""
        if device.action != "add":
            return
        _LOGGER.debug(
            "Discovered Device at path: %s, triggering scan serial",
            device.device_path,
        )
        self.scan_serial()

    @callback
    def _async_process_discovered_usb_device(self, device: USBDevice) -> None:
        """Process a USB discovery."""
        _LOGGER.debug("Discovered USB Device: %s", device)
        device_tuple = dataclasses.astuple(device)
        if device_tuple in self.seen:
            return
        self.seen.add(device_tuple)
        for matcher in self.usb:
            if "vid" in matcher and device.vid != matcher["vid"]:
                continue
            if "pid" in matcher and device.pid != matcher["pid"]:
                continue
            flow: USBFlow = {
                "domain": matcher["domain"],
                "context": {"source": config_entries.SOURCE_USB},
                "data": dataclasses.asdict(device),
            }
            self.flow_dispatcher.async_create(flow)

    @callback
    def _async_process_ports(self, ports: list[ListPortInfo]) -> None:
        """Process each discovered port."""
        for port in ports:
            if port.vid is None and port.pid is None:
                continue
            self._async_process_discovered_usb_device(usb_device_from_port(port))

    def scan_serial(self) -> None:
        """Scan serial ports."""
        self.hass.add_job(self._async_process_ports, comports())

    async def _async_scan_serial(self) -> None:
        """Scan serial ports."""
        self._async_process_ports(await self.hass.async_add_executor_job(comports))

    async def async_request_scan_serial(self) -> None:
        """Request a serial scan."""
        if not self._request_debouncer:
            self._request_debouncer = Debouncer(
                self.hass,
                _LOGGER,
                cooldown=REQUEST_SCAN_COOLDOWN,
                immediate=True,
                function=self._async_scan_serial,
            )
        await self._request_debouncer.async_call()


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "usb/scan"})
@websocket_api.async_response
async def websocket_usb_scan(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict,
) -> None:
    """Scan for new usb devices."""
    usb_discovery: USBDiscovery = hass.data[DOMAIN]
    if not usb_discovery.observer_active:
        await usb_discovery.async_request_scan_serial()
    connection.send_result(msg["id"])

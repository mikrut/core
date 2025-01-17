"""Support for ThinkingCleaner switches."""
from __future__ import annotations

from datetime import timedelta
import time

from pythinkingcleaner import Discovery, ThinkingCleaner
import voluptuous as vol

from homeassistant import util
from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import CONF_HOST, STATE_OFF, STATE_ON
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import ToggleEntity, ToggleEntityDescription

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(milliseconds=100)

MIN_TIME_TO_WAIT = timedelta(seconds=5)
MIN_TIME_TO_LOCK_UPDATE = 5

SWITCH_TYPES: tuple[ToggleEntityDescription, ...] = (
    ToggleEntityDescription(
        key="clean",
        name="Clean",
    ),
    ToggleEntityDescription(
        key="dock",
        name="Dock",
    ),
    ToggleEntityDescription(
        key="find",
        name="Find",
    ),
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({vol.Optional(CONF_HOST): cv.string})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the ThinkingCleaner platform."""
    host = config.get(CONF_HOST)
    if host:
        devices = [ThinkingCleaner(host, "unknown")]
    else:
        discovery = Discovery()
        devices = discovery.discover()

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update_devices():
        """Update all devices."""
        for device_object in devices:
            device_object.update()

    entities = [
        ThinkingCleanerSwitch(device, update_devices, description)
        for device in devices
        for description in SWITCH_TYPES
    ]

    add_entities(entities)


class ThinkingCleanerSwitch(ToggleEntity):
    """ThinkingCleaner Switch (dock, clean, find me)."""

    def __init__(self, tc_object, update_devices, description: ToggleEntityDescription):
        """Initialize the ThinkingCleaner."""
        self.entity_description = description

        self._update_devices = update_devices
        self._tc_object = tc_object
        self._state = (
            self._tc_object.is_cleaning if description.key == "clean" else False
        )
        self.lock = False
        self.last_lock_time = None
        self.graceful_state = False

        self._attr_name = f"{tc_object} {description.name}"

    def lock_update(self):
        """Lock the update since TC clean takes some time to update."""
        if self.is_update_locked():
            return
        self.lock = True
        self.last_lock_time = time.time()

    def reset_update_lock(self):
        """Reset the update lock."""
        self.lock = False
        self.last_lock_time = None

    def set_graceful_lock(self, state):
        """Set the graceful state."""
        self.graceful_state = state
        self.reset_update_lock()
        self.lock_update()

    def is_update_locked(self):
        """Check if the update method is locked."""
        if self.last_lock_time is None:
            return False

        if time.time() - self.last_lock_time >= MIN_TIME_TO_LOCK_UPDATE:
            self.last_lock_time = None
            return False

        return True

    @property
    def is_on(self):
        """Return true if device is on."""
        if self.entity_description.key == "clean":
            return (
                self.graceful_state
                if self.is_update_locked()
                else self._tc_object.is_cleaning
            )

        return False

    def turn_on(self, **kwargs):
        """Turn the device on."""
        sensor_type = self.entity_description.key
        if sensor_type == "clean":
            self.set_graceful_lock(True)
            self._tc_object.start_cleaning()
        elif sensor_type == "dock":
            self._tc_object.dock()
        elif sensor_type == "find":
            self._tc_object.find_me()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        if self.entity_description.key == "clean":
            self.set_graceful_lock(False)
            self._tc_object.stop_cleaning()

    def update(self):
        """Update the switch state (Only for clean)."""
        if self.entity_description.key == "clean" and not self.is_update_locked():
            self._tc_object.update()
            self._state = STATE_ON if self._tc_object.is_cleaning else STATE_OFF

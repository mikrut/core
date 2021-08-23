"""Support for Sonarr sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DATA_GIGABYTES
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SonarrDataUpdateCoordinator
from .entity import SonarrEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sonarr sensors based on a config entry."""
    coordinator: SonarrDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        SonarrCommandsSensor(coordinator, entry.entry_id),
        SonarrDiskspaceSensor(coordinator, entry.entry_id),
        SonarrQueueSensor(coordinator, entry.entry_id),
        SonarrSeriesSensor(coordinator, entry.entry_id),
        SonarrUpcomingSensor(coordinator, entry.entry_id),
        SonarrWantedSensor(coordinator, entry.entry_id),
    ]

    async_add_entities(entities, True)


class SonarrSensor(SonarrEntity, SensorEntity):
    """Implementation of the Sonarr sensor."""

    def __init__(
        self,
        *,
        coordinator: SonarrDataUpdateCoordinator,
        entry_id: str,
        enabled_default: bool = True,
        icon: str,
        key: str,
        name: str,
        unit_of_measurement: str | None = None,
    ) -> None:
        """Initialize Sonarr sensor."""
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_entity_registry_enabled_default = enabled_default

        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            device_id=entry_id,
        )

    async def async_update(self) -> None:
        """Update the entity."""
        if not self.enabled:
            return

        if self.key not in ("diskspace"):
            self.coordinator.enable_datapoint(self._datapoint)

        await super().async_update()

    async def async_will_remove_from_hass(self) -> None:
        """Disable additional datapoint for sensor data."""
        if self.key not in ("diskspace"):
            self.coordinator.disable_datapoint(self._datapoint)

        await super().async_will_remove_from_hass()

    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes of the entity."""
        attrs = {}

        if self.key == "diskspace":
            app = self.coordinator.sonarr.app
        for disk in app.disks:
            free = disk.free / 1024 ** 3
            total = disk.total / 1024 ** 3
            usage = free / total * 100

            attrs[
                disk.path
            ] = f"{free:.2f}/{total:.2f}{self.unit_of_measurement} ({usage:.2f}%)"
        elif self.key == "commands" and self.coordinator.data.get("commands") is not None:
            for command in self.coordinator.data["commands"]:
                attrs[command.name] = command.state
        elif self.key == "queue" and self.coordinator.data.get("queue") is not None:
            for item in self.coordinator.data["queue"]:
                remaining = 1 if item.size == 0 else item.size_remaining / item.size
                remaining_pct = 100 * (1 - remaining)
                name = f"{item.episode.series.title} {item.episode.identifier}"
                attrs[name] = f"{remaining_pct:.2f}%"
        elif self.key == "series" and self.coordinator.data.get("series") is not None:
            for item in self.coordinator.data["series"]:
                attrs[item.series.title] = f"{item.downloaded}/{item.episodes} Episodes"
        elif self.key == "upcoming" and self.coordinator.data.get("upcoming") is not None:
            for episode in self.coordinator.data["upcoming"]:
                attrs[episode.series.title] = episode.identifier
        elif self.key == "wanted" and self.coordinator.data.get("wanted") is not None:
            for episode in self.coordinator.data["wanted"].episodes:
                name = f"{episode.series.title} {episode.identifier}"
                attrs[name] = episode.airdate

        return attrs

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if self.key == "diskspace":
            total_free = sum(disk.free for disk in app.disks)
            free = total_free / 1024 ** 3
            return f"{free:.2f}"

        if self.key == "commands" and self.coordinator.data.get("commands") is not None:
            return len(self.coordinator.data["commands"])

        if self.key == "queue" and self.coordinator.data.get("queue") is not None:
            return len(self.coordinator.data["queue"])

        if self.key == "series" and self.coordinator.data.get("series") is not None:
            return len(self.coordinator.data["series"])

        if self.key == "upcoming" and self.coordinator.data.get("upcoming") is not None:
            return len(self.coordinator.data["upcoming"])

        if self.key == "wanted" and self.coordinator.data.get("wanted") is not None:
            return self.coordinator.data["wanted"].total

        return None


class SonarrCommandsSensor(SonarrSensor):
    """Defines a Sonarr Commands sensor."""

    def __init__(self, coordinator: SonarrDataUpdateCoordinator, entry_id: str) -> None:
        """Initialize Sonarr Commands sensor."""
        self._commands = []

        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            icon="mdi:code-braces",
            key="commands",
            name=f"{coordinator.sonarr.app.info.app_name} Commands",
            unit_of_measurement="Commands",
            enabled_default=False,
        )


class SonarrDiskspaceSensor(SonarrSensor):
    """Defines a Sonarr Disk Space sensor."""

    def __init__(self, coordinator: SonarrDataUpdateCoordinator, entry_id: str) -> None:
        """Initialize Sonarr Disk Space sensor."""
        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            icon="mdi:harddisk",
            key="diskspace",
            name=f"{coordinator.sonarr.app.info.app_name} Disk Space",
            unit_of_measurement=DATA_GIGABYTES,
            enabled_default=False,
        )     


class SonarrQueueSensor(SonarrSensor):
    """Defines a Sonarr Queue sensor."""

    def __init__(self, coordinator: SonarrDataUpdateCoordinator, entry_id: str) -> None:
        """Initialize Sonarr Queue sensor."""
        self._queue = []

        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            icon="mdi:download",
            key="queue",
            name=f"{coordinator.sonarr.app.info.app_name} Queue",
            unit_of_measurement="Episodes",
            enabled_default=False,
        )


class SonarrSeriesSensor(SonarrSensor):
    """Defines a Sonarr Series sensor."""

    def __init__(self, coordinator: SonarrDataUpdateCoordinator, entry_id: str) -> None:
        """Initialize Sonarr Series sensor."""
        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            icon="mdi:television",
            key="series",
            name=f"{coordinator.sonarr.app.info.app_name} Shows",
            unit_of_measurement="Series",
            enabled_default=False,
        )


class SonarrUpcomingSensor(SonarrSensor):
    """Defines a Sonarr Upcoming sensor."""

    def __init__(self, coordinator: SonarrDataUpdateCoordinator, entry_id: str) -> None:
        """Initialize Sonarr Upcoming sensor."""
        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            icon="mdi:television",
            key="upcoming",
            name=f"{coordinator.sonarr.app.info.app_name} Upcoming",
            unit_of_measurement="Episodes",
        )


class SonarrWantedSensor(SonarrSensor):
    """Defines a Sonarr Wanted sensor."""

    def __init__(self, coordinator: SonarrDataUpdateCoordinator, entry_id: str) -> None:
        """Initialize Sonarr Wanted sensor."""
        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            icon="mdi:television",
            key="wanted",
            name=f"{coordinator.sonarr.app.info.app_name} Wanted",
            unit_of_measurement="Episodes",
            enabled_default=False,
        )

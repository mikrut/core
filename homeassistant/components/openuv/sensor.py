"""Support for OpenUV sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TIME_MINUTES, UV_INDEX
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import as_local, parse_datetime

from . import OpenUV, OpenUvEntity
from .const import (
    DATA_CLIENT,
    DATA_UV,
    DOMAIN,
    TYPE_CURRENT_OZONE_LEVEL,
    TYPE_CURRENT_UV_INDEX,
    TYPE_CURRENT_UV_LEVEL,
    TYPE_MAX_UV_INDEX,
    TYPE_SAFE_EXPOSURE_TIME_1,
    TYPE_SAFE_EXPOSURE_TIME_2,
    TYPE_SAFE_EXPOSURE_TIME_3,
    TYPE_SAFE_EXPOSURE_TIME_4,
    TYPE_SAFE_EXPOSURE_TIME_5,
    TYPE_SAFE_EXPOSURE_TIME_6,
)

ATTR_MAX_UV_TIME = "time"

EXPOSURE_TYPE_MAP = {
    TYPE_SAFE_EXPOSURE_TIME_1: "st1",
    TYPE_SAFE_EXPOSURE_TIME_2: "st2",
    TYPE_SAFE_EXPOSURE_TIME_3: "st3",
    TYPE_SAFE_EXPOSURE_TIME_4: "st4",
    TYPE_SAFE_EXPOSURE_TIME_5: "st5",
    TYPE_SAFE_EXPOSURE_TIME_6: "st6",
}

UV_LEVEL_EXTREME = "Extreme"
UV_LEVEL_VHIGH = "Very High"
UV_LEVEL_HIGH = "High"
UV_LEVEL_MODERATE = "Moderate"
UV_LEVEL_LOW = "Low"

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=TYPE_CURRENT_OZONE_LEVEL,
        name="Current Ozone Level",
        icon="mdi:vector-triangle",
        native_unit_of_measurement="du",
    ),
    SensorEntityDescription(
        key=TYPE_CURRENT_UV_INDEX,
        name="Current UV Index",
        icon="mdi:weather-sunny",
        native_unit_of_measurement=UV_INDEX,
    ),
    SensorEntityDescription(
        key=TYPE_CURRENT_UV_LEVEL,
        name="Current UV Level",
        icon="mdi:weather-sunny",
        native_unit_of_measurement=None,
    ),
    SensorEntityDescription(
        key=TYPE_MAX_UV_INDEX,
        name="Max UV Index",
        icon="mdi:weather-sunny",
        native_unit_of_measurement=UV_INDEX,
    ),
    SensorEntityDescription(
        key=TYPE_SAFE_EXPOSURE_TIME_1,
        name="Skin Type 1 Safe Exposure Time",
        icon="mdi:timer-outline",
        native_unit_of_measurement=TIME_MINUTES,
    ),
    SensorEntityDescription(
        key=TYPE_SAFE_EXPOSURE_TIME_2,
        name="Skin Type 2 Safe Exposure Time",
        icon="mdi:timer-outline",
        native_unit_of_measurement=TIME_MINUTES,
    ),
    SensorEntityDescription(
        key=TYPE_SAFE_EXPOSURE_TIME_3,
        name="Skin Type 3 Safe Exposure Time",
        icon="mdi:timer-outline",
        native_unit_of_measurement=TIME_MINUTES,
    ),
    SensorEntityDescription(
        key=TYPE_SAFE_EXPOSURE_TIME_4,
        name="Skin Type 4 Safe Exposure Time",
        icon="mdi:timer-outline",
        native_unit_of_measurement=TIME_MINUTES,
    ),
    SensorEntityDescription(
        key=TYPE_SAFE_EXPOSURE_TIME_5,
        name="Skin Type 5 Safe Exposure Time",
        icon="mdi:timer-outline",
        native_unit_of_measurement=TIME_MINUTES,
    ),
    SensorEntityDescription(
        key=TYPE_SAFE_EXPOSURE_TIME_6,
        name="Skin Type 6 Safe Exposure Time",
        icon="mdi:timer-outline",
        native_unit_of_measurement=TIME_MINUTES,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a OpenUV sensor based on a config entry."""
    openuv = hass.data[DOMAIN][DATA_CLIENT][entry.entry_id]

    entities = [OpenUvSensor(openuv, description) for description in SENSOR_TYPES]
    async_add_entities(entities, True)


class OpenUvSensor(OpenUvEntity, SensorEntity):
    """Define a binary sensor for OpenUV."""

    def __init__(
        self,
        openuv: OpenUV,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(openuv, description.key)
        self.entity_description = description

    @callback
    def update_from_latest_data(self) -> None:
        """Update the state."""
        data = self.openuv.data[DATA_UV].get("result")

        if not data:
            self._attr_available = False
            return

        self._attr_available = True

        if self._sensor_type == TYPE_CURRENT_OZONE_LEVEL:
            self._attr_native_value = data["ozone"]
        elif self._sensor_type == TYPE_CURRENT_UV_INDEX:
            self._attr_native_value = data["uv"]
        elif self._sensor_type == TYPE_CURRENT_UV_LEVEL:
            if data["uv"] >= 11:
                self._attr_native_value = UV_LEVEL_EXTREME
            elif data["uv"] >= 8:
                self._attr_native_value = UV_LEVEL_VHIGH
            elif data["uv"] >= 6:
                self._attr_native_value = UV_LEVEL_HIGH
            elif data["uv"] >= 3:
                self._attr_native_value = UV_LEVEL_MODERATE
            else:
                self._attr_native_value = UV_LEVEL_LOW
        elif self._sensor_type == TYPE_MAX_UV_INDEX:
            self._attr_native_value = data["uv_max"]
            uv_max_time = parse_datetime(data["uv_max_time"])
            if uv_max_time:
                self._attr_extra_state_attributes.update(
                    {ATTR_MAX_UV_TIME: as_local(uv_max_time)}
                )
        elif self._sensor_type in (
            TYPE_SAFE_EXPOSURE_TIME_1,
            TYPE_SAFE_EXPOSURE_TIME_2,
            TYPE_SAFE_EXPOSURE_TIME_3,
            TYPE_SAFE_EXPOSURE_TIME_4,
            TYPE_SAFE_EXPOSURE_TIME_5,
            TYPE_SAFE_EXPOSURE_TIME_6,
        ):
            self._attr_native_value = data["safe_exposure_time"][
                EXPOSURE_TYPE_MAP[self._sensor_type]
            ]

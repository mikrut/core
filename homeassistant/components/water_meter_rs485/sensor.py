"""Sensor for RS485 water meter."""

from homeassistant.components.sensor import (
    DEVICE_CLASS_GAS,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import VOLUME_CUBIC_METERS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity

from .const import DOMAIN, CONF_METER_ID_1, CONF_METER_ID_2


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    conf = config_entry.data
    master = hass.data[DOMAIN][config_entry.entry_id]["master"]

    entities = []
    for id_key in [CONF_METER_ID_1, CONF_METER_ID_2]:
        if conf.get(id_key):
            entities.append(
                Du15Sensor(
                    unique_id=str(conf[id_key]),
                    master=master,
                    hass=hass,
                )
            )

    if entities:
        async_add_entities(
            new_entities=entities,
            update_before_add=True,
        )


class Du15Sensor(SensorEntity):
    """DU-15 Water Meter Sensor"""

    def __init__(
        self,
        unique_id: str,
        master,
        hass: HomeAssistant,
    ) -> None:
        """Init this sensor."""
        self._unique_id = unique_id
        self._master = master
        self._hass = hass
        self.entity_description = SensorEntityDescription(
            key="water_meter_dg15",
            name=f"Water Meter {self._unique_id}",
            icon="mdi:water",
        )

        self._attr_unique_id = unique_id
        self._attr_device_class = DEVICE_CLASS_GAS
        self._attr_state_class = STATE_CLASS_TOTAL_INCREASING
        self._attr_native_unit_of_measurement = VOLUME_CUBIC_METERS
        self._attr_native_value = None

    async def async_update(self):
        volume = await self._hass.async_add_executor_job(
            self._master.read_value, self._unique_id
        )
        self._attr_native_value = volume

    @property
    def device_info(self) -> entity.DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self._unique_id)},
            "manufacturer": "OOO NPP TEPLOVODOKHRAN",
            "model": "Pulsar DU-15",
            "name": self.name,
        }

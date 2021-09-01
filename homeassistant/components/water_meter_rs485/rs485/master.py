""" Water Meter RS485 bus master """

from decimal import Decimal
from os import stat
import threading
from typing import Any, Mapping, Optional

import serial

from homeassistant.components.water_meter_rs485.const import (
    CONF_BAUDRATE,
    CONF_BYTE_SIZE,
    CONF_PARITY,
    CONF_SERIAL_PORT,
    CONF_STOP_BITS,
    ByteSizeType,
    ParityType,
    StopBitsType,
)

from .protocol import ReadVolumeRequest, ReadVolumeResponse


class Master:
    def __init__(self, config: Mapping[str, Any]):
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

    def read_value(self, unique_id: str) -> Optional[Decimal]:
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

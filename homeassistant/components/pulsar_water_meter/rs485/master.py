""" Water Meter RS485 bus master """

from decimal import Decimal
from os import stat
import threading
from typing import Any, Mapping, Optional

import serial
from serial.serialutil import SerialException

from homeassistant.components.pulsar_water_meter.const import (
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
    WRITE_TIMEOUT = 1
    READ_TIMEOUT = 1

    def __init__(self, config: Mapping[str, Any]):
        self._serial_port = serial.Serial(
            port=None,
            baudrate=config[CONF_BAUDRATE],
            bytesize=ByteSizeType.get_by_description(config[CONF_BYTE_SIZE]),
            parity=ParityType.get_by_description(config[CONF_PARITY]),
            stopbits=StopBitsType.get_by_description(config[CONF_STOP_BITS]),
            write_timeout=Master.WRITE_TIMEOUT,
            timeout=Master.READ_TIMEOUT,
        )
        self._serial_port.port = config[CONF_SERIAL_PORT]
        self._lock = threading.Lock()

    def open(self) -> bool:
        with self._lock:
            try:
                self._serial_port.open()
            except SerialException:
                return False
            return True

    def read_value(self, unique_id: str) -> Optional[Decimal]:
        with self._lock:
            if not self._serial_port.is_open:
                try:
                    self._serial_port.open()
                except SerialException:
                    return False
            self._serial_port.reset_input_buffer()

            sensor_id = int(unique_id)

            read_frame = ReadVolumeRequest(address=sensor_id).frame
            bytes_written = self._serial_port.write(read_frame.to_bytes())
            assert bytes_written == read_frame.length

            response_frame = self._serial_port.read(
                ReadVolumeResponse.EXPECTED_TOTAL_LENGTH
            )
            if len(response_frame) != ReadVolumeResponse.EXPECTED_TOTAL_LENGTH:
                return None

            response = ReadVolumeResponse(response_frame)
            assert response.address == sensor_id
            assert response.id == read_frame.id
            return response.volume

"""Constants for the Water Meter RS485 integration."""

import enum

import serial
import voluptuous as vol

import homeassistant.helpers.config_validation as cv

DOMAIN = "water_meter_rs485"

CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_BYTE_SIZE = "byte_size"
CONF_PARITY = "parity"
CONF_STOP_BITS = "stop_bits"


class ParityType(enum.Enum):
    """Possible options for parity."""

    none = (
        "None",
        serial.PARITY_NONE,
    )
    even = (
        "Even",
        serial.PARITY_EVEN,
    )
    odd = (
        "Odd",
        serial.PARITY_ODD,
    )
    mark = (
        "Mark",
        serial.PARITY_MARK,
    )
    space = (
        "Space",
        serial.PARITY_SPACE,
    )

    @classmethod
    def list(cls) -> list[str]:
        """Return a list of descriptions."""
        return [e.description for e in ParityType]

    @classmethod
    def get_by_description(cls, description: str) -> str:
        """Get parity by description"""
        for parity in cls:
            if parity.description == description:
                return parity.parity
        raise ValueError

    def __init__(self, description: str, parity) -> None:
        """Init instance."""
        self._description = description
        self._parity = parity

    @property
    def parity(self):
        """Return parity."""
        return self._parity

    @property
    def description(self) -> str:
        """Return parity description."""
        return self._description


class StopBitsType(enum.Enum):
    """Possible values for stop bits."""

    one = (
        "One",
        serial.STOPBITS_ONE,
    )
    two = (
        "Two",
        serial.STOPBITS_TWO,
    )

    @classmethod
    def list(cls) -> list[str]:
        """Return a list of descriptions"""
        return [e.description for e in StopBitsType]

    @classmethod
    def get_by_description(cls, description: str) -> str:
        """Get stop bits by description"""
        for stopbits in cls:
            if stopbits.description == description:
                return stopbits.stop_bits
        raise ValueError

    def __init__(self, description: str, stop_bits) -> None:
        """Init instance."""
        self._description = description
        self._stop_bits = stop_bits

    @property
    def stop_bits(self):
        """Return stop_bits."""
        return self._stop_bits

    @property
    def description(self) -> str:
        """Return stop bits description."""
        return self._description


class ByteSizeType(enum.Enum):
    """Possible values for byte size."""

    fivebits = (
        "Five bits",
        serial.FIVEBITS,
    )
    sixbits = (
        "Six bits",
        serial.SIXBITS,
    )
    sevenbits = (
        "Seven bits",
        serial.SEVENBITS,
    )
    eightbits = (
        "Eight bits",
        serial.EIGHTBITS,
    )

    @classmethod
    def list(cls) -> list[str]:
        """Return a list of descriptions"""
        return [e.description for e in ByteSizeType]

    @classmethod
    def get_by_description(cls, description: str) -> str:
        """Get byte size by description"""
        for bytesize in cls:
            if bytesize.description == description:
                return bytesize.bytesize
        raise ValueError

    def __init__(self, description: str, bytesize) -> None:
        """Init instance."""
        self._description = description
        self._bytesize = bytesize

    @property
    def bytesize(self):
        """Return byte size."""
        return self._bytesize

    @property
    def description(self) -> str:
        """Return byte size description."""
        return self._description


DEFAULT_BAUDRATE = 9600
DEFAULT_BYTE_SIZE = ByteSizeType.eightbits
DEFAULT_PARITY = ParityType.none
DEFAULT_STOP_BITS = StopBitsType.one

CONF_WATERMETER_RS485_PORT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): cv.positive_int,
        vol.Required(CONF_BYTE_SIZE, default=DEFAULT_BYTE_SIZE.description): vol.In(
            sorted(ByteSizeType.list())
        ),
        vol.Required(CONF_PARITY, default=DEFAULT_PARITY.description): vol.In(
            sorted(ParityType.list())
        ),
        vol.Required(CONF_STOP_BITS, default=DEFAULT_STOP_BITS.description): vol.In(
            sorted(StopBitsType.list())
        ),
    }
)

SIGNAL_ADD_ENTITIES = "water_meter_rs485_add_new_entities"

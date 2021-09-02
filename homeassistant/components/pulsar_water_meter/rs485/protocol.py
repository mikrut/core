""" Water Meter RS485 protocol """

from decimal import Decimal
import enum
import random

import libscrc


@enum.unique
class PulsarFunction(enum.Enum):
    READ_MEASUREMENTS = 0x01
    READ_SYSTEM_TIME = 0x04
    WRITE_SYSTEM_TIME = 0x05
    READ_ARCHIVES = 0x06
    READ_PARAMS = 0x0A
    WRITE_PARAMS = 0x0B


class PulsarFrame:
    ADDRESS_LENGTH_BYTES = 4
    FUNCTION_LENGTH_BYTES = 1
    LENGTH_LENGTH_BYTES = 1
    ID_LENGTH_BYTES = 2
    CRC_LENGTH_BYTES = 2

    NONDATA_LENGTH_BYTES = (
        ADDRESS_LENGTH_BYTES
        + FUNCTION_LENGTH_BYTES
        + LENGTH_LENGTH_BYTES
        + ID_LENGTH_BYTES
        + CRC_LENGTH_BYTES
    )

    LENGTH_BYTE_INDEX = ADDRESS_LENGTH_BYTES + FUNCTION_LENGTH_BYTES

    ADDRESS_ENDIANNESS = "big"
    ID_ENDIANNESS = "big"  # arbitrary, not specified in protocol
    CRC_ENDIANNESS = "little"

    def __init__(
        self,
        address: int,
        function: PulsarFunction,
        data: bytes,
        id: int = None,
    ):
        self.address = address
        self.function = function
        self.data = data
        self.id = id if id is not None else random.randint(0x0000, 0xFFFF)

    @property
    def length(self):
        return PulsarFrame.NONDATA_LENGTH_BYTES + len(self.data)

    @staticmethod
    def _to_bcd(num: int) -> int:
        bcd = 0
        bit_index = 0
        while num > 0:
            last_digit = num % 10
            bcd |= last_digit << bit_index

            num //= 10
            bit_index += 4
        return bcd

    @staticmethod
    def _from_bcd(bcd: int) -> int:
        num = 0
        digit_coeff = 1
        while bcd > 0:
            last_digit = bcd & 0x0F
            assert 0 <= last_digit and last_digit <= 10
            num += last_digit * digit_coeff

            bcd >>= 4
            digit_coeff *= 10
        return num

    def to_bytes(self) -> bytes:
        frame = bytearray()
        bcd_address = PulsarFrame._to_bcd(self.address)
        frame += int.to_bytes(
            bcd_address,
            length=PulsarFrame.ADDRESS_LENGTH_BYTES,
            byteorder=PulsarFrame.ADDRESS_ENDIANNESS,
        )
        frame.append(self.function.value)

        frame.append(0x00)  # length byte

        frame += self.data
        frame += int.to_bytes(
            self.id,
            length=PulsarFrame.ID_LENGTH_BYTES,
            byteorder=PulsarFrame.ID_ENDIANNESS,
        )

        length = len(frame) + PulsarFrame.CRC_LENGTH_BYTES
        assert length == self.length
        frame[PulsarFrame.LENGTH_BYTE_INDEX] = length

        crc16 = PulsarFrame._compute_crc(frame)
        frame += int.to_bytes(
            crc16,
            length=PulsarFrame.CRC_LENGTH_BYTES,
            byteorder=PulsarFrame.CRC_ENDIANNESS,
        )

        return frame

    @staticmethod
    def _compute_crc(data: bytes) -> bytes:
        return libscrc.modbus(data)

    @staticmethod
    def from_bytes(frame: bytearray) -> "PulsarFrame":
        assert len(frame) > PulsarFrame.LENGTH_BYTE_INDEX

        current_pos = 0

        def extract_bytes(length: int) -> bytes:
            nonlocal current_pos
            end_pos = current_pos + length
            result = frame[current_pos:end_pos]
            current_pos = end_pos
            return result

        def extract_byte(length: int) -> int:
            assert length == 1
            return extract_bytes(length=1)[0]

        address_bcd = int.from_bytes(
            extract_bytes(PulsarFrame.ADDRESS_LENGTH_BYTES),
            byteorder=PulsarFrame.ADDRESS_ENDIANNESS,
        )
        address = PulsarFrame._from_bcd(address_bcd)
        function = PulsarFunction(extract_byte(PulsarFrame.FUNCTION_LENGTH_BYTES))
        length = extract_byte(PulsarFrame.LENGTH_LENGTH_BYTES)
        assert len(frame) == length
        data_length = length - PulsarFrame.NONDATA_LENGTH_BYTES
        data = extract_bytes(data_length)
        id = int.from_bytes(
            extract_bytes(PulsarFrame.ID_LENGTH_BYTES),
            byteorder=PulsarFrame.ID_ENDIANNESS,
        )
        crc = int.from_bytes(
            extract_bytes(PulsarFrame.CRC_LENGTH_BYTES),
            byteorder=PulsarFrame.CRC_ENDIANNESS,
        )

        expected_crc = PulsarFrame._compute_crc(frame[: -PulsarFrame.CRC_LENGTH_BYTES])
        assert expected_crc == crc

        return PulsarFrame(address=address, function=function, data=data, id=id)


class ReadVolumeRequest:
    def __init__(self, address: int):
        self.frame = PulsarFrame(
            address=address,
            function=PulsarFunction.READ_MEASUREMENTS,
            data=bytes([0x01, 0x00, 0x00, 0x00]),
        )

    @property
    def id(self) -> int:
        return self.frame.id


class ReadVolumeResponse:
    VOLUME_ENDIANNESS = "little"
    VOLUME_UNITS_IN_M3 = 1000

    EXPECTED_DATA_LENGTH = 4
    EXPECTED_TOTAL_LENGTH = EXPECTED_DATA_LENGTH + PulsarFrame.NONDATA_LENGTH_BYTES

    def __init__(self, data: bytes):
        self.frame = PulsarFrame.from_bytes(data)
        assert self.frame.length == ReadVolumeResponse.EXPECTED_TOTAL_LENGTH
        assert self.frame.function == PulsarFunction.READ_MEASUREMENTS

    @property
    def address(self) -> int:
        return self.frame.address

    @property
    def id(self) -> int:
        return self.frame.id

    @property
    def volume(self) -> Decimal:
        volume_units = Decimal(
            int.from_bytes(
                self.frame.data, byteorder=ReadVolumeResponse.VOLUME_ENDIANNESS
            )
        )
        volume = volume_units / ReadVolumeResponse.VOLUME_UNITS_IN_M3
        return volume

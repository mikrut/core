"""Test the Water Meter RS485 protocol."""
from decimal import Decimal
import homeassistant.components.water_meter_rs485.protocol as protocol
import pytest


class FrameData(object):
    def __init__(self, address, function, data, id):
        self.address = address
        self.function = function
        self.data = data
        self.id = id


@pytest.mark.parametrize(
    "frame_and_result",
    [
        (
            FrameData(
                address=12345678,
                function=0x01,
                data=bytes.fromhex("01000000"),
                id=0xFDEC,
            ),
            bytes.fromhex("12345678010E01000000FDEC3996"),
        ),
        (
            FrameData(
                address=12345678,
                function=0x04,
                data=bytes.fromhex("0C0717091F1A"),
                id=0x788A,
            ),
            bytes.fromhex("1234567804100C0717091F1A788A1E1C"),
        ),
        (
            FrameData(
                address=12345678,
                function=0x06,
                data=bytes.fromhex("0100000001000C07170000000C0717090000"),
                id=0xF2F7,
            ),
            bytes.fromhex("12345678061C0100000001000C07170000000C0717090000F2F7C51D"),
        ),
    ],
)
def test_pulsar_frame_correctness(frame_and_result):
    frame, result = frame_and_result

    encoded_frame = protocol.PulsarFrame(
        address=frame.address,
        function=protocol.PulsarFunction(frame.function),
        data=frame.data,
        id=frame.id,
    )
    assert result == encoded_frame.to_bytes()

    decoded_frame = protocol.PulsarFrame.from_bytes(result)
    assert decoded_frame.address == frame.address
    assert decoded_frame.function == protocol.PulsarFunction(frame.function)
    assert decoded_frame.length == len(result)
    assert decoded_frame.data == frame.data
    assert decoded_frame.id == frame.id


def test_pulsar_frame_fills_id():
    frame = protocol.PulsarFrame(
        address=12345678,
        function=protocol.PulsarFunction.READ_ARCHIVES,
        data=bytes.fromhex("00"),
    )
    assert frame.id is not None


def test_pulsar_read_volume_request():
    address = 12345678
    read_request = protocol.ReadVolumeRequest(address=address)

    frame = read_request.frame
    assert frame.address == address
    assert frame.function == protocol.PulsarFunction.READ_MEASUREMENTS
    assert frame.length == 0x0E
    assert frame.data == bytes.fromhex("01000000")
    assert frame.id is not None


def test_pulsar_read_volume_response():
    data = bytes.fromhex("12345678010E8BA40000DCAB0F47")
    expected_address = 12345678
    expected_volume = Decimal(42123) / 1000
    expected_id = 0xDCAB

    read_response = protocol.ReadVolumeResponse(data=data)
    assert read_response.address == expected_address
    assert read_response.volume == expected_volume
    assert read_response.id == expected_id

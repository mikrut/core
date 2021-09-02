"""Test the Water Meter RS485 config flow."""
from unittest.mock import patch, Mock

from homeassistant import config_entries, setup
from homeassistant.components.pulsar_water_meter.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)

LIST_PORTS_FUNCTION = "serial.tools.list_ports.comports"
GET_SERIAL_BY_ID_FUNCTION = (
    "homeassistant.components.pulsar_water_meter.config_flow.get_serial_by_id"
)


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    comport_str = "Comport Mock"
    comport_serial = "ab12cd34ef56"
    comport_manufacturer = "Hoofs and Horns Inc."
    comport_device = "/dev/fakeTty1"
    get_serial_result = "/dev/fakeTtyAcm1"

    comport_mock = Mock(
        serial_number=comport_serial,
        manufacturer=comport_manufacturer,
        device=comport_device,
    )
    comport_mock.__str__ = Mock(return_value=comport_str)

    user_selection = (
        f"{comport_str}, s/n: {comport_serial or 'n/a'} - {comport_manufacturer}"
    )

    user_input = {
        "serial_port": user_selection,
        "baudrate": 9600,
        "byte_size": "8",
        "parity": "None",
        "stop_bits": "1",
        "meter_id_1": 123456789,
        "meter_id_2": 987654321,
    }

    with patch(
        LIST_PORTS_FUNCTION,
        return_value=[comport_mock],
    ) as list_ports_mock, patch(
        GET_SERIAL_BY_ID_FUNCTION,
        return_value=get_serial_result,
    ) as get_serial_by_id_mock:
        await setup.async_setup_component(hass, "persistent_notification", {})
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == RESULT_TYPE_FORM
        assert result["errors"] is None
        assert len(list_ports_mock.mock_calls) == 1
        assert len(get_serial_by_id_mock.mock_calls) == 0

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input,
        )
        await hass.async_block_till_done()

    user_input["serial_port"] = get_serial_result

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == user_selection
    assert result2["data"] == user_input
    assert len(list_ports_mock.mock_calls) == 2
    get_serial_by_id_mock.assert_called_once_with(comport_device)
    assert len(comport_mock.__str__.mock_calls) == 2


async def test_form_no_comports_available(hass: HomeAssistant) -> None:
    with patch(
        LIST_PORTS_FUNCTION,
        return_value=[],
    ) as list_ports_mock:
        await setup.async_setup_component(hass, "persistent_notification", {})
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == RESULT_TYPE_ABORT
        assert result["reason"] == "no_serial_port"
        assert len(list_ports_mock.mock_calls) == 1

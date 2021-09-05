"""Config flow for sm_center_api integration."""
from __future__ import annotations

import logging
from typing import Any, List
import aiohttp

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from aiohttp import ClientSession, ClientResponse
import urllib.parse as urlparse

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            "host", default="https://api.sm-center.ru/ukrk"
        ): str,  # vol.Url(),
        vol.Required("phone"): cv.positive_int,
        vol.Required("password"): str,
    }
)


class Meter:
    def __init__(
        self, id: int, ident: str, factory_number: str, resource: str, units: str
    ):
        self.id = id
        self.ident = ident
        self.factory_number = factory_number
        self.resource = resource
        self.units = units

    @classmethod
    def from_json(cls, json):
        return cls(
            id=json["ID"],
            ident=json["Ident"],
            factory_number=json["FactoryNumber"],
            resource=json["Resource"],
            units=json["Units"],
        )


class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(
        self, websession: ClientSession, host: str, phone: int, password: str
    ) -> None:
        """Initialize."""
        self.websession = websession
        self.host = host
        self.phone = phone
        self.password = password
        self.access_token = None
        self.user_info = None
        self.company_info = None
        self.authenticated = False

        if not self.host[-1] == "/":
            self.host += "/"

    @classmethod
    def from_config(cls, websession: ClientSession, config):
        result = cls(
            websession=websession,
            host=config["host"],
            phone=config["phone"],
            password=config["password"],
        )
        result.access_token = config["access_token"]
        result.user_info = config["user_info"]
        result.company_info = config["company_info"]
        result.authenticated = True
        return result

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        endpoint = urlparse.urljoin(self.host, "auth/login")
        try:
            response = await self.websession.post(
                endpoint, json={"phone": self.phone, "password": self.password}
            )
            async with response:
                if response.status != 200:
                    return False
                response_json = await response.json()
                assert len(response_json["accounts"]) > 0

                self.access_token = response_json["acx"]
                self.user_info = {
                    "email": response_json["email"],
                    "fio": response_json["fio"],
                }
                company_account = response_json["accounts"][0]
                self.company_info = {
                    "address": company_account["address"],
                    "company": company_account["company"],
                    "metersStartDay": company_account["metersStartDay"],
                    "metersEndDay": company_account["metersEndDay"],
                }
                self.authenticated = True
                return True
        except aiohttp.ClientError:
            raise CannotConnect

    async def meters_list(self) -> list[Meter]:
        assert self.authenticated
        endpoint = urlparse.urljoin(self.host, "Meters/List")
        response = await self.websession.get(
            endpoint, headers={"acx": self.access_token}
        )
        async with response:
            if response.status == 401:
                self.authenticated = False
                raise Exception("Unauthenticated")
            if response.status != 200:
                raise Exception("Unknown error")
            response_json = await response.json()
            return [Meter.from_json(meter) for meter in response_json["Data"]]

    async def meters_save_value(self, meter: Meter, value: float):
        assert self.authenticated
        endpoint = urlparse.urljoin(self.host, "Meters/SaveMeterValue")
        if False:
            response = await self.websession.post(
                endpoint,
                headers={"acx": self.access_token},
                json={
                    "ID": meter.id,
                    "Value": value,
                    "ValueT2": None,
                    "ValueT3": None,
                },
            )
            async with response:
                if response.status == 401:
                    self.authenticated = False
                    raise Exception("Unauthenticated")
                if response.status != 200:
                    raise Exception("Unknown error")

    @property
    def company(self) -> str:
        assert self.authenticated
        return self.company_info["company"]

    @property
    def config(self):
        assert self.authenticated
        return {
            "host": self.host,
            "phone": self.phone,
            "password": self.password,
            "access_token": self.access_token,
            "user_info": self.user_info,
            "company_info": self.company_info,
        }

    async def unload(self):
        await self.websession.close()


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    async with aiohttp.ClientSession() as session:
        hub = PlaceholderHub(session, data["host"], data["phone"], data["password"])

        if not await hub.authenticate():
            raise InvalidAuth

        return {"api": hub.config, "title": hub.company}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for sm_center_api."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=info)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

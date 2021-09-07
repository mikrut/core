from aiohttp import ClientSession, ClientResponse
from homeassistant.exceptions import HomeAssistantError

import urllib.parse as urlparse
import logging
import aiohttp


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


class HouseholdApi:
    """
    API to access household info and send measurements
    to the housing and communal services
    """

    def __init__(
        self, websession: ClientSession, host: str, phone: int, password: str
    ) -> None:
        """Initialize."""
        self.websession = websession
        self.host = HouseholdApi._fix_host(host)
        self.phone = phone
        self.password = password
        self.access_token = None
        self.user_info = None
        self.company_info = None
        self.authenticated = False

    @staticmethod
    def _fix_host(host):
        if not host[-1] == "/":
            host += "/"
        return host

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

    def set_access_token(self, access_token):
        self.access_token = access_token
        self.authenticated = True

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        endpoint = urlparse.urljoin(self.host, "auth/login")
        try:
            response = await self.websession.post(
                endpoint, json={"phone": self.phone, "password": self.password}
            )
            async with response:
                if response.status != 200:
                    logging.error(
                        "Received invalid authentication status code: %s",
                        response.status,
                    )
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


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

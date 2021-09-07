from homeassistant.components.sm_center_api.household_api import HouseholdApi, Meter
from pytest_aiohttp import aiohttp_server, aiohttp_client
from aiohttp import web

import random


TEST_PHONE = 79860123456
TEST_PASSWORD = "secret_password"
TEST_ACX = "abcd1234/ABCD5678"

TEST_METER_ID = 1
TEST_METER_IDENT = "2"
TEST_METER_FACTORY_NUMBER = "ABC 123-01/456"
TEST_METER_RESOURCE = "Hot water"
TEST_METER_UNITS = "m3"

ANOTHER_METER_ID = 2
ANOTHER_METER_IDENT = "3"
ANOTHER_METER_FACTORY_NUMBER = "DEF 456-02/567"
ANOTHER_METER_RESOURCE = "Hot water"
ANOTHER_METER_UNITS = "m3"


def meter_json(id, ident, factory_number, resource, units):
    return {
        "Address": "Baker St., 221B",
        "AutoValueGettingOnly": False,
        "CustomName": None,
        "FactoryNumber": factory_number,
        "HouseId": 1,
        "ID": id,
        "Ident": ident,
        "IsDisabled": False,
        "LastCheckupDate": "01.01.1970",
        "Name": None,
        "NextCheckupDate": "01.01.1974",
        "NumberOfDecimalPlaces": 3,
        "NumberOfIntegerPart": 9,
        "PeriodMessage": "message1",
        "RecheckInterval": 4,
        "Resource": resource,
        "StartDate": "01.01.1970",
        "StartValue": 0.0,
        "StartValueT2": None,
        "StartValueT3": None,
        "Tariff1Name": None,
        "Tariff2Name": None,
        "Tariff3Name": None,
        "TariffNumber": "single tariff",
        "TariffNumberInt": 1,
        "UniqueNum": "000001",
        "Units": units,
        "Values": [
            {
                "IsCurrentPeriod": False,
                "Kind": "Registered",
                "Period": "23.08.2021",
                "Value": 104.0,
                "ValueT2": None,
                "ValueT3": None,
            },
            {
                "IsCurrentPeriod": False,
                "Kind": "Reported",
                "Period": "19.08.2021",
                "Value": 104.0,
                "ValueT2": None,
                "ValueT3": None,
            },
            {
                "IsCurrentPeriod": False,
                "Kind": "Registered",
                "Period": "23.07.2021",
                "Value": 102.0,
                "ValueT2": None,
                "ValueT3": None,
            },
        ],
        "ValuesCanAdd": False,
        "ValuesEndDay": 22,
        "ValuesPeriodEndIsCurrent": False,
        "ValuesPeriodStartIsCurrent": True,
        "ValuesStartDay": 15,
    }


async def test_authentication_method(aiohttp_server, aiohttp_client) -> None:
    """Test if we can authenticate"""
    test_phone = TEST_PHONE
    test_password = TEST_PASSWORD
    test_acx = TEST_ACX

    async def login_handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data["phone"] == test_phone
        assert data["password"] == test_password

        phone = str(data["phone"])
        phone_formatted = f"{phone[:-7]}-{phone[-7:-4]}-{phone[-4:-2]}-{phone[-2:]}"

        return web.json_response(
            {
                "login": str(data["phone"]),
                "isDispatcher": False,
                "accounts": [
                    {
                        "id": 123,
                        "ident": "982342342",
                        "fio": "982342342",
                        "address": "Chernomorsk",
                        "company": "Hoofs and Horns",
                        "cn": None,
                        "metersStartDay": 15,
                        "metersEndDay": 22,
                        "metersAccessFlag": False,
                        "metersPeriodStartIsCurrent": True,
                        "metersPeriodEndIsCurrent": True,
                        "phone": phone_formatted,
                        "allowPassRequestCreation": False,
                        "denyRequestCreation": False,
                        "denyRequestCreationMessage": None,
                    },
                ],
                "email": "i.i.ivanov@example.com",
                "phone": phone,
                "fio": "Ivan Ivanovich Ivanov",
                "birthday": None,
                "acx": test_acx,
                "companyPhone": "",
                "accessOSS": False,
                "userSettings": None,
            },
        )

    app = web.Application()
    app.router.add_post("/auth/login", login_handler)
    server = await aiohttp_server(app)

    client = await aiohttp_client(app)
    api = HouseholdApi(
        client.session,
        host=str(client.make_url("/")),
        phone=test_phone,
        password=test_password,
    )
    assert (await api.authenticate()) is True
    assert api.access_token == test_acx


async def test_get_meters_list(aiohttp_server, aiohttp_client) -> None:
    test_acx = TEST_ACX
    test_meters_list = [
        meter_json(
            id=TEST_METER_ID,
            ident=TEST_METER_IDENT,
            factory_number=TEST_METER_FACTORY_NUMBER,
            resource=TEST_METER_RESOURCE,
            units=TEST_METER_UNITS,
        ),
        meter_json(
            id=ANOTHER_METER_ID,
            ident=ANOTHER_METER_IDENT,
            factory_number=ANOTHER_METER_FACTORY_NUMBER,
            resource=ANOTHER_METER_RESOURCE,
            units=ANOTHER_METER_UNITS,
        ),
    ]
    random.shuffle(test_meters_list)

    async def meters_list_handler(request: web.Request) -> web.Response:
        assert request.headers["acx"] == test_acx
        return web.json_response({"Data": test_meters_list})

    app = web.Application()
    app.router.add_get("/Meters/List", meters_list_handler)
    server = await aiohttp_server(app)

    client = await aiohttp_client(app)
    api = HouseholdApi(
        client.session,
        host=str(client.make_url("/")),
        phone=TEST_PHONE,
        password=TEST_PASSWORD,
    )
    api.set_access_token(TEST_ACX)

    meters_list = await api.meters_list()
    assert len(meters_list) == len(test_meters_list)
    for test_meter, meter in zip(test_meters_list, meters_list):
        assert (
            meter.id,
            meter.ident,
            meter.factory_number,
            meter.resource,
            meter.units,
        ) == (
            test_meter["ID"],
            test_meter["Ident"],
            test_meter["FactoryNumber"],
            test_meter["Resource"],
            test_meter["Units"],
        )


async def test_save_meters_value(aiohttp_server, aiohttp_client) -> None:
    test_acx = TEST_ACX
    test_meter_value = 100.0

    test_meter = Meter(
        id=TEST_METER_ID,
        ident=TEST_METER_IDENT,
        factory_number=TEST_METER_FACTORY_NUMBER,
        resource=TEST_METER_RESOURCE,
        units=TEST_METER_UNITS,
    )

    async def meters_save_handler(request: web.Request) -> web.Response:
        assert request.headers["acx"] == test_acx

        data = await request.json()
        assert data["ID"] == test_meter.id
        assert data["Value"] == test_meter_value
        assert data["ValueT2"] is None
        assert data["ValueT3"] is None

        return web.Response(status=200)

    app = web.Application()
    app.router.add_post("/Meters/SaveMeterValue", meters_save_handler)
    server = await aiohttp_server(app)

    client = await aiohttp_client(app)
    api = HouseholdApi(
        client.session,
        host=str(client.make_url("/")),
        phone=TEST_PHONE,
        password=TEST_PASSWORD,
    )
    api.set_access_token(TEST_ACX)

    await api.meters_save_value(test_meter, test_meter_value)

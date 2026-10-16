"""Firmware telemetry on image requests, merged with Bluetooth readings."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import pytest

from custom_components.paperlessoffline.ble import SETTING_CHARACTERISTICS
from custom_components.paperlessoffline.const import BLE_CHAR_TELEMETRY, CONF_TELEMETRY, DOMAIN
from custom_components.paperlessoffline.frame import parse_wake_status

from .conftest import CLIENT_ID, TOKEN
from .test_phase3 import ADDRESS, fake_session  # noqa: F401

IMAGE_URL = f"/api/paperlessoffline/{TOKEN}/image.bmp"
SETTINGS_URL = f"/api/paperlessoffline/{TOKEN}/settings.json"
WAKE = "?voltage=4012&usb=0&charging=1&orientation=2&width=800&height=480&fw=1.2.3"


def test_parse_ignores_bad_values() -> None:
    assert parse_wake_status({"voltage": "x", "usb": "2", "charging": "1", "orientation": "9"}) == {
        "charging": True
    }
    assert parse_wake_status({}) == {}


async def test_wake_feeds_entities(hass: HomeAssistant, hass_client_no_auth, loaded_entry) -> None:
    client = await hass_client_no_auth()
    await client.get(IMAGE_URL + WAKE)
    await hass.async_block_till_done()
    voltage = hass.states.get("sensor.kitchen_battery_voltage")
    assert float(voltage.state) == pytest.approx(4.012)
    assert voltage.attributes["source"] == "wake"
    assert voltage.attributes["last_read"]
    assert hass.states.get("binary_sensor.kitchen_charging").state == "on"
    assert hass.states.get("binary_sensor.kitchen_usb_power").state == "off"
    assert hass.states.get("sensor.kitchen_last_seen").attributes["telemetry"]["fw"] == "1.2.3"


async def test_orientation_sensor(hass: HomeAssistant, hass_client_no_auth, loaded_entry) -> None:
    entry = er.async_get(hass).async_get("sensor.kitchen_orientation")
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert entry.entity_category is er.EntityCategory.DIAGNOSTIC
    # Enabled entities start without a value.
    manager = loaded_entry.runtime_data
    client = await hass_client_no_auth()
    await client.get(IMAGE_URL + WAKE)
    assert manager.status_reading("orientation")[0] == 2


async def test_newest_reading_wins_and_last_value_is_kept(
    hass: HomeAssistant,
    hass_client_no_auth,
    loaded_entry,
    fake_session,  # noqa: F811
    freezer: FrozenDateTimeFactory,
) -> None:
    from datetime import timedelta

    manager = loaded_entry.runtime_data
    client = await hass_client_no_auth()
    await client.get(IMAGE_URL + WAKE)
    freezer.tick(timedelta(minutes=5))
    assert await manager.async_ble_sync(ADDRESS)
    await hass.async_block_till_done()
    voltage = hass.states.get("sensor.kitchen_battery_voltage")
    assert float(voltage.state) == pytest.approx(3.912)
    assert voltage.attributes["source"] == "bluetooth"

    freezer.tick(timedelta(minutes=5))
    await client.get(IMAGE_URL + "?voltage=3800")
    await hass.async_block_till_done()
    voltage = hass.states.get("sensor.kitchen_battery_voltage")
    assert float(voltage.state) == pytest.approx(3.8)
    assert voltage.attributes["source"] == "wake"
    # usb was not in the newest request: the Bluetooth value stays, flagged as such.
    usb = hass.states.get("binary_sensor.kitchen_usb_power")
    assert usb.state == "on"
    assert usb.attributes["source"] == "bluetooth"

    # Old firmware or telemetry off: requests without params change nothing.
    freezer.tick(timedelta(hours=2))
    await client.get(IMAGE_URL)
    await hass.async_block_till_done()
    assert float(hass.states.get("sensor.kitchen_battery_voltage").state) == pytest.approx(3.8)


async def test_firmware_version_updates_device_and_persists(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry
) -> None:
    devices = dr.async_get(hass)
    assert (
        devices.async_get_device_by_identifier(
            (DOMAIN, CLIENT_ID), loaded_entry.entry_id
        ).sw_version
        == "offline firmware"
    )
    client = await hass_client_no_auth()
    await client.get(IMAGE_URL + WAKE)
    assert (
        devices.async_get_device_by_identifier(
            (DOMAIN, CLIENT_ID), loaded_entry.entry_id
        ).sw_version
        == "1.2.3"
    )
    assert loaded_entry.runtime_data.state.fw == "1.2.3"

    await hass.config_entries.async_reload(loaded_entry.entry_id)
    await hass.async_block_till_done()
    assert loaded_entry.runtime_data.state.fw == "1.2.3"
    assert (
        devices.async_get_device_by_identifier(
            (DOMAIN, CLIENT_ID), loaded_entry.entry_id
        ).sw_version
        == "1.2.3"
    )


async def test_telemetry_switch(hass: HomeAssistant, hass_client_no_auth, loaded_entry) -> None:
    client = await hass_client_no_auth()
    assert hass.states.get("switch.kitchen_telemetry").state == "on"
    assert (await (await client.get(SETTINGS_URL)).json())["telemetry"] is True
    manager = loaded_entry.runtime_data
    assert not manager.pending_changes()

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.kitchen_telemetry"}, blocking=True
    )
    assert loaded_entry.options[CONF_TELEMETRY] is False
    assert manager.pending_changes()
    assert (await (await client.get(SETTINGS_URL)).json())["telemetry"] is False


async def test_telemetry_written_over_ble(
    hass: HomeAssistant,
    loaded_entry,
    fake_session,  # noqa: F811
) -> None:
    assert ("telemetry", BLE_CHAR_TELEMETRY) in SETTING_CHARACTERISTICS
    manager = loaded_entry.runtime_data
    await manager.async_ble_sync(ADDRESS, force_provision=True)
    assert fake_session.instances[0].written[0]["telemetry"] is True

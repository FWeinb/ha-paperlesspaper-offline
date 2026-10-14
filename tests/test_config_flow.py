"""Config and options flow tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from habluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.paperlessoffline.ble import FrameBleError
from custom_components.paperlessoffline.const import (
    CONF_CLIENT_ID,
    CONF_PANEL,
    CONF_TOKEN,
    DOMAIN,
)

from .conftest import CLIENT_ID, TOKEN


@pytest.fixture(autouse=True)
def internal_url(hass: HomeAssistant) -> None:
    hass.config.internal_url = "http://192.168.1.10:8123"


@pytest.fixture
def ble_info() -> BluetoothServiceInfoBleak:
    info = AsyncMock(spec=BluetoothServiceInfoBleak)
    info.name = CLIENT_ID
    info.address = "34:85:18:8F:1D:CA"
    return info


async def test_manual_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CLIENT_ID: "not-a-frame"}
    )
    assert result["errors"] == {CONF_CLIENT_ID: "invalid_client_id"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CLIENT_ID: CLIENT_ID.upper(), "name": "Kitchen"}
    )
    assert result["step_id"] == "urls"
    assert result["description_placeholders"]["image_url"].startswith(
        "http://192.168.1.10:8123/api/paperlessoffline/"
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kitchen"
    assert result["data"][CONF_CLIENT_ID] == CLIENT_ID
    assert result["data"][CONF_PANEL] == "epd7"
    assert len(result["data"][CONF_TOKEN]) >= 24
    assert result["options"]["mounting"] == "portrait"


async def test_manual_flow_duplicate(hass: HomeAssistant, loaded_entry) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CLIENT_ID: CLIENT_ID}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_manual_flow_no_internal_url(hass: HomeAssistant) -> None:
    hass.config.internal_url = None
    with patch(
        "custom_components.paperlessoffline.config_flow.async_frame_base_url",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CLIENT_ID: CLIENT_ID}
        )
    assert result["reason"] == "no_internal_url"


async def test_bluetooth_flow_provisions(hass: HomeAssistant, ble_info) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=ble_info
    )
    assert result["step_id"] == "bluetooth_confirm"
    with patch("custom_components.paperlessoffline.config_flow.async_provision") as provision:
        provision.side_effect = [FrameBleError("gone"), None]
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"name": "Hall", "provision": True, "wifi": {}}
        )
        assert result["errors"] == {"base": "provision_failed"}
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"name": "Hall", "provision": True, "wifi": {}}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    address, settings, wifi = provision.call_args.args[1:]
    assert wifi is None
    assert address == ble_info.address
    token = result["data"][CONF_TOKEN]
    assert settings["settingsUrl"] == (
        f"http://192.168.1.10:8123/api/paperlessoffline/{token}/settings.json"
    )
    assert settings["downloadUrl"].endswith(f"/{token}/image.bmp")


async def test_bluetooth_flow_manual_fallback(hass: HomeAssistant, ble_info) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=ble_info
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Hall", "provision": False, "wifi": {}}
    )
    assert result["step_id"] == "urls"


async def test_bluetooth_not_a_frame(hass: HomeAssistant, ble_info) -> None:
    ble_info.name = "SomethingElse"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=ble_info
    )
    assert result["reason"] == "not_supported"


async def test_options_flow(hass: HomeAssistant, loaded_entry) -> None:
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert TOKEN in result["description_placeholders"]["image_url"]
    base = {
        "interval": 90,
        "order": "shuffle",
        "mounting": "portrait",
        "quiet_hours": {
            "quiet_enabled": True,
            "quiet_start": "23:00:00",
            "quiet_end": "06:30:00",
            "quiet_suppress_motion": True,
        },
        "rendering": {
            "palette": "pure",
            "dither": "default",
            "serpentine": "on",
            "fit": "contain",
            "background": "default",
            "saturation": 1.3,
        },
        "authentication": {"auth_enabled": True, "auth_user": "frame"},
        "regenerate_token": True,
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], base)
    assert result["errors"] == {"base": "auth_incomplete"}
    base["authentication"]["auth_password"] = "pw"
    result = await hass.config_entries.options.async_configure(result["flow_id"], base)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    opts = loaded_entry.options
    assert opts["interval"] == 5400
    assert opts["mounting"] == "portrait"
    assert opts["quiet_start"] == "23:00:00"
    assert opts["render_defaults"] == {
        "palette": "pure",
        "serpentine": True,
        "fit": "contain",
        "saturation": 1.3,
    }
    assert loaded_entry.data[CONF_TOKEN] != TOKEN
    manager = loaded_entry.runtime_data
    assert manager.canvas.width == 480
    from custom_components.paperlessoffline.data import DATA_KEY

    assert set(hass.data[DATA_KEY].tokens) == {loaded_entry.data[CONF_TOKEN]}


async def test_bluetooth_flow_with_wifi(hass: HomeAssistant, ble_info) -> None:
    from custom_components.paperlessoffline.ble import WifiConnectError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=ble_info
    )
    with patch("custom_components.paperlessoffline.config_flow.async_provision") as provision:
        provision.side_effect = [WifiConnectError("nope"), None]
        form = {
            "name": "Hall",
            "provision": True,
            "wifi": {"wifi_ssid": "Home", "wifi_password": "pw"},
        }
        result = await hass.config_entries.flow.async_configure(result["flow_id"], form)
        assert result["errors"] == {"base": "wifi_failed"}
        result = await hass.config_entries.flow.async_configure(result["flow_id"], form)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert provision.call_args.args[3] == ("Home", "pw")
    assert result["data"]["provisioned_token"] == result["data"][CONF_TOKEN]
    assert result["data"]["provisioned_base_url"] == "http://192.168.1.10:8123"


async def test_manual_flow_with_url_host(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CLIENT_ID: CLIENT_ID, "url_host": "localhost"}
    )
    assert result["errors"] == {"url_host": "unusable_host"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CLIENT_ID: CLIENT_ID, "url_host": "10.0.0.7"}
    )
    assert result["description_placeholders"]["settings_url"].startswith("http://10.0.0.7:8123/")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["options"]["url_host"] == "10.0.0.7"
    assert result["data"]["provisioned_base_url"] == "http://10.0.0.7:8123"

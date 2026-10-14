"""BLE provisioning."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from bleak.exc import BleakError
from homeassistant.core import HomeAssistant
import pytest

from custom_components.paperlessoffline.ble import FrameBleError, async_provision
from custom_components.paperlessoffline.const import (
    BLE_CHAR_COMMAND,
    BLE_CHAR_DOWNLOAD_URL,
    BLE_CHAR_IMAGE_MODE,
    BLE_CHAR_MOTION_WAKEUP,
    BLE_CHAR_SETTINGS_URL,
    BLE_CHAR_TIMEOUT,
)

ADDRESS = "34:85:18:8F:1D:CA"


@pytest.fixture
def client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_ble(client: AsyncMock):
    with (
        patch(
            "homeassistant.components.bluetooth.async_ble_device_from_address",
            return_value=MagicMock(),
        ) as from_address,
        patch(
            "custom_components.paperlessoffline.ble.establish_connection",
            AsyncMock(return_value=client),
        ),
    ):
        yield from_address


async def test_provision_writes_in_order(hass: HomeAssistant, client, mock_ble) -> None:
    await async_provision(
        hass,
        ADDRESS,
        {
            "settingsUrl": "http://ha/s.json",
            "downloadUrl": "http://ha/i.bmp",
            "timeout": 3600,
            "motionWakeup": True,
        },
    )
    writes = [(c.args[0], c.args[1]) for c in client.write_gatt_char.call_args_list]
    assert writes == [
        (BLE_CHAR_SETTINGS_URL, b"http://ha/s.json"),
        (BLE_CHAR_DOWNLOAD_URL, b"http://ha/i.bmp"),
        (BLE_CHAR_TIMEOUT, b"3600"),
        (BLE_CHAR_MOTION_WAKEUP, b"1"),
        (BLE_CHAR_IMAGE_MODE, b"1"),
        (BLE_CHAR_COMMAND, b"SAVE_SETTINGS"),
        (BLE_CHAR_COMMAND, b"EXIT_SETUP"),
    ]
    client.disconnect.assert_awaited()


async def test_exit_setup_disconnect_is_fine(hass: HomeAssistant, client, mock_ble) -> None:
    async def write(uuid, data, response):
        if data == b"EXIT_SETUP":
            raise BleakError("disconnected")

    client.write_gatt_char.side_effect = write
    await async_provision(hass, ADDRESS, {"timeout": 60})


async def test_provision_errors(hass: HomeAssistant, client, mock_ble) -> None:
    client.write_gatt_char.side_effect = BleakError("boom")
    with pytest.raises(FrameBleError):
        await async_provision(hass, ADDRESS, {"timeout": 60})
    mock_ble.return_value = None
    with pytest.raises(FrameBleError):
        await async_provision(hass, ADDRESS, {"timeout": 60})

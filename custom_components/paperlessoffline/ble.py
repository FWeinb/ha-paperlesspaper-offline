"""BLE GATT client for frames in setup mode (single button press)."""

from __future__ import annotations

from collections.abc import Mapping
import contextlib
import logging

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.core import HomeAssistant

from .const import (
    BLE_CHAR_AUTH_PASSWORD,
    BLE_CHAR_AUTH_USER,
    BLE_CHAR_AUTO_ROTATION,
    BLE_CHAR_CHARGER_MODE,
    BLE_CHAR_COMMAND,
    BLE_CHAR_DOWNLOAD_URL,
    BLE_CHAR_IMAGE_MODE,
    BLE_CHAR_MOTION_WAKEUP,
    BLE_CHAR_SETTINGS_URL,
    BLE_CHAR_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

# Settings JSON key -> characteristic; written in this order.
SETTING_CHARACTERISTICS: tuple[tuple[str, str], ...] = (
    ("settingsUrl", BLE_CHAR_SETTINGS_URL),
    ("downloadUrl", BLE_CHAR_DOWNLOAD_URL),
    ("timeout", BLE_CHAR_TIMEOUT),
    ("httpAuthUser", BLE_CHAR_AUTH_USER),
    ("httpAuthPassword", BLE_CHAR_AUTH_PASSWORD),
    ("motionWakeup", BLE_CHAR_MOTION_WAKEUP),
    ("autoRotation", BLE_CHAR_AUTO_ROTATION),
    ("chargerMode", BLE_CHAR_CHARGER_MODE),
)


class FrameBleError(Exception):
    """Talking to the frame over BLE failed."""


def _encode(value: object) -> bytes:
    if isinstance(value, bool):
        return b"1" if value else b"0"
    return str(value).encode()


async def async_provision(
    hass: HomeAssistant, address: str, settings: Mapping[str, object]
) -> None:
    """Write URLs and settings to a frame in setup mode, save, and exit setup."""
    # Imported lazily so the integration works on systems without Bluetooth.
    from homeassistant.components import bluetooth  # noqa: PLC0415

    device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
    if device is None:
        raise FrameBleError("Frame is not reachable over Bluetooth")
    try:
        client = await establish_connection(
            BleakClientWithServiceCache, device, address, max_attempts=3
        )
    except (BleakError, TimeoutError) as err:
        raise FrameBleError(str(err)) from err
    try:
        for key, uuid in SETTING_CHARACTERISTICS:
            if key in settings:
                await client.write_gatt_char(uuid, _encode(settings[key]), response=True)
        await client.write_gatt_char(BLE_CHAR_IMAGE_MODE, b"1", response=True)
        await client.write_gatt_char(BLE_CHAR_COMMAND, b"SAVE_SETTINGS", response=True)
        try:
            await client.write_gatt_char(BLE_CHAR_COMMAND, b"EXIT_SETUP", response=True)
        except (BleakError, TimeoutError):
            _LOGGER.debug("Frame disconnected while exiting setup mode")
    except (BleakError, TimeoutError) as err:
        raise FrameBleError(str(err)) from err
    finally:
        with contextlib.suppress(BleakError, TimeoutError):
            await client.disconnect()

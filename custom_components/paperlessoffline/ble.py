"""BLE GATT client for frames in setup mode (single button press)."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import contextlib
import json
import logging
from typing import Any, Self

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
    BLE_CHAR_SYSTEM_INFO,
    BLE_CHAR_TIMEOUT,
    BLE_CHAR_WIFI_CONNECTED,
    BLE_CHAR_WIFI_INFO,
    BLE_CHAR_WIFI_PASSWORD,
    BLE_CHAR_WIFI_SSID,
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

# The firmware tries a new WiFi network for up to 10 s, then reports via BLE.
WIFI_TIMEOUT = 20.0
WIFI_POLL = 1.0


class FrameBleError(Exception):
    """Talking to the frame over BLE failed."""


class WifiConnectError(FrameBleError):
    """The frame could not join the given WiFi network."""


def _encode(value: object) -> bytes:
    if isinstance(value, bool):
        return b"1" if value else b"0"
    return str(value).encode()


def _json(raw: bytes | bytearray) -> dict[str, Any]:
    try:
        data = json.loads(bytes(raw).decode("utf-8", "replace") or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


class FrameSession:
    """One BLE connection to a frame in setup mode.

    Use as ``async with FrameSession(hass, address) as session: ...``.
    """

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        """Initialise."""
        self.hass = hass
        self.address = address
        self._client: BleakClientWithServiceCache | None = None

    async def __aenter__(self) -> Self:
        """Connect."""
        # Imported lazily so the integration works on systems without Bluetooth.
        from homeassistant.components import bluetooth  # noqa: PLC0415

        device = bluetooth.async_ble_device_from_address(self.hass, self.address, connectable=True)
        if device is None:
            raise FrameBleError("Frame is not reachable over Bluetooth")
        try:
            self._client = await establish_connection(
                BleakClientWithServiceCache, device, self.address, max_attempts=3
            )
        except (BleakError, TimeoutError) as err:
            raise FrameBleError(str(err)) from err
        return self

    async def __aexit__(self, *exc: object) -> None:
        """Disconnect."""
        if self._client is not None:
            with contextlib.suppress(BleakError, TimeoutError):
                await self._client.disconnect()
            self._client = None

    @property
    def client(self) -> BleakClientWithServiceCache:
        """The connected client."""
        if self._client is None:
            raise FrameBleError("Not connected")
        return self._client

    async def _write(self, uuid: str, data: bytes) -> None:
        try:
            await self.client.write_gatt_char(uuid, data, response=True)
        except (BleakError, TimeoutError) as err:
            raise FrameBleError(str(err)) from err

    async def _read(self, uuid: str) -> bytes:
        try:
            return bytes(await self.client.read_gatt_char(uuid))
        except (BleakError, TimeoutError) as err:
            raise FrameBleError(str(err)) from err

    async def read_status(self) -> dict[str, Any]:
        """Battery, power and WiFi status."""
        system = _json(await self._read(BLE_CHAR_SYSTEM_INFO))
        wifi = _json(await self._read(BLE_CHAR_WIFI_INFO))
        status: dict[str, Any] = {}
        if isinstance(system.get("voltage"), int | float):
            status["voltage"] = int(system["voltage"])
        for key in ("usb", "charging"):
            if isinstance(system.get(key), bool):
                status[key] = system[key]
        if isinstance(wifi.get("rssi"), int | float):
            status["rssi"] = int(wifi["rssi"])
        if isinstance(wifi.get("ip"), str):
            status["ip"] = wifi["ip"]
        return status

    async def wifi_connected(self) -> bool:
        """Whether the frame reports a WiFi connection."""
        raw = await self._read(BLE_CHAR_WIFI_CONNECTED)
        return bool(raw) and raw[0] == 1

    async def set_wifi(self, ssid: str, password: str) -> None:
        """Set WiFi credentials and wait until the frame has joined the network.

        The firmware only stores the credentials when the connection works.
        """
        await self._write(BLE_CHAR_WIFI_SSID, ssid.encode())
        # Writing the password starts the connection test.
        await self._write(BLE_CHAR_WIFI_PASSWORD, password.encode())
        loop = asyncio.get_running_loop()
        deadline = loop.time() + WIFI_TIMEOUT
        await asyncio.sleep(WIFI_POLL * 2)
        while loop.time() < deadline:
            if await self.wifi_connected():
                return
            await asyncio.sleep(WIFI_POLL)
        raise WifiConnectError(f"Frame could not connect to {ssid!r}")

    async def write_settings(self, settings: Mapping[str, object]) -> None:
        """Write settings (keys as in the settings JSON, plus ``settingsUrl``)."""
        for key, uuid in SETTING_CHARACTERISTICS:
            if key in settings:
                await self._write(uuid, _encode(settings[key]))
        if "downloadUrl" in settings:
            await self._write(BLE_CHAR_IMAGE_MODE, b"1")

    async def save(self) -> None:
        """Persist written settings on the frame."""
        await self._write(BLE_CHAR_COMMAND, b"SAVE_SETTINGS")

    async def exit_setup(self) -> None:
        """Leave setup mode; the frame then updates and sleeps."""
        try:
            await self.client.write_gatt_char(BLE_CHAR_COMMAND, b"EXIT_SETUP", response=True)
        except (BleakError, TimeoutError):
            _LOGGER.debug("Frame disconnected while exiting setup mode")


async def async_provision(
    hass: HomeAssistant,
    address: str,
    settings: Mapping[str, object],
    wifi: tuple[str, str] | None = None,
) -> None:
    """Optionally set WiFi, then write URLs and settings, save, and exit setup."""
    async with FrameSession(hass, address) as session:
        if wifi:
            await session.set_wifi(*wifi)
        await session.write_settings(settings)
        await session.save()
        await session.exit_setup()

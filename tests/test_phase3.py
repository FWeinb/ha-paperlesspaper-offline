"""Bluetooth sync, entities, repair issues, fix flow, migration and URLs."""

from __future__ import annotations

from datetime import timedelta
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperlessoffline.const import (
    CONF_BLE_AUTO,
    CONF_CLIENT_ID,
    CONF_MOTION_WAKEUP,
    CONF_PANEL,
    CONF_PROVISIONED_BASE,
    CONF_PROVISIONED_TOKEN,
    CONF_TOKEN,
    DOMAIN,
)
from custom_components.paperlessoffline.issues import ISSUE_OFFLINE, ISSUE_REPROVISION, issue_id
from custom_components.paperlessoffline.urls import async_frame_base_url

from .conftest import CLIENT_ID, TOKEN

ADDRESS = "34:85:18:8F:1D:CA"
SETTINGS_URL = f"/api/paperlessoffline/{TOKEN}/settings.json"


class FakeSession:
    """Stands in for FrameSession."""

    instances: ClassVar[list[FakeSession]] = []

    def __init__(self, hass, address) -> None:
        self.address = address
        self.written: list[dict] = []
        self.saved = False
        self.exited = False
        FakeSession.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def read_status(self):
        return {"voltage": 3912, "usb": True, "charging": True, "rssi": -61}

    async def write_settings(self, settings) -> None:
        self.written.append(dict(settings))

    async def save(self) -> None:
        self.saved = True

    async def exit_setup(self) -> None:
        self.exited = True


@pytest.fixture
def fake_session():
    FakeSession.instances = []
    with patch("custom_components.paperlessoffline.frame.FrameSession", FakeSession):
        yield FakeSession


def _issue(hass: HomeAssistant, kind: str, entry) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, issue_id(kind, entry.entry_id))


async def test_ble_sync_reads_status_and_pushes_settings(
    hass: HomeAssistant, loaded_entry, fake_session
) -> None:
    manager = loaded_entry.runtime_data
    hass.config_entries.async_update_entry(
        loaded_entry, options={**loaded_entry.options, CONF_MOTION_WAKEUP: True}
    )
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.kitchen_in_sync").state == "off"

    assert await manager.async_ble_sync(ADDRESS)
    await hass.async_block_till_done()
    session = fake_session.instances[0]
    assert session.written[0]["motionWakeup"] is True
    assert "settingsUrl" not in session.written[0]  # URLs only when reprovisioning
    assert session.saved and not session.exited
    assert hass.states.get("binary_sensor.kitchen_in_sync").state == "on"
    voltage = hass.states.get("sensor.kitchen_battery_voltage")
    assert float(voltage.state) == pytest.approx(3.912)
    assert voltage.attributes["last_read"]
    assert hass.states.get("binary_sensor.kitchen_charging").state == "on"
    assert hass.states.get("binary_sensor.kitchen_usb_power").state == "on"


async def test_ble_sync_without_changes_only_reads(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, fake_session
) -> None:
    client = await hass_client_no_auth()
    await client.get(SETTINGS_URL)  # frame fetched current settings
    assert await loaded_entry.runtime_data.async_ble_sync(ADDRESS)
    assert fake_session.instances[0].written == []


async def test_ble_seen_respects_option_and_cooldown(hass: HomeAssistant, loaded_entry) -> None:
    manager = loaded_entry.runtime_data
    with patch.object(manager, "async_ble_sync", AsyncMock(return_value=True)) as sync:
        manager.async_ble_seen(ADDRESS)
        await hass.async_block_till_done()
        manager.async_ble_seen(ADDRESS)  # within cooldown
        await hass.async_block_till_done()
        assert sync.await_count == 1

        manager._ble_last_attempt = 0
        hass.config_entries.async_update_entry(
            loaded_entry, options={**loaded_entry.options, CONF_BLE_AUTO: False}
        )
        manager.async_ble_seen(ADDRESS)
        await hass.async_block_till_done()
        assert sync.await_count == 1


async def test_offline_issue(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer
) -> None:
    manager = loaded_entry.runtime_data
    client = await hass_client_no_auth()
    await client.get(SETTINGS_URL)
    # The frame reaches HA at the URL HA itself reports, so this is "offline", not "new URLs".
    hass.config.internal_url = "http://192.168.1.10:8123"
    hass.config_entries.async_update_entry(
        loaded_entry,
        data={**loaded_entry.data, CONF_PROVISIONED_BASE: "http://192.168.1.10:8123"},
    )
    assert _issue(hass, ISSUE_OFFLINE, loaded_entry) is None

    freezer.tick(timedelta(hours=4))
    await manager.async_refresh_base_url()
    issue = _issue(hass, ISSUE_OFFLINE, loaded_entry)
    assert issue is not None and not issue.is_fixable
    assert issue.translation_placeholders["name"] == "Kitchen"

    await client.get(SETTINGS_URL)
    assert _issue(hass, ISSUE_OFFLINE, loaded_entry) is None


async def test_token_change_needs_reprovision(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, fake_session
) -> None:
    manager = loaded_entry.runtime_data
    hass.config_entries.async_update_entry(
        loaded_entry, data={**loaded_entry.data, CONF_TOKEN: "new-token-xxxxxxxxxxxxxxxx"}
    )
    await hass.async_block_till_done()
    manager.async_update_issues()
    issue = _issue(hass, ISSUE_REPROVISION, loaded_entry)
    assert issue is not None and issue.is_fixable
    assert issue.translation_key == "reprovision_token"

    # The next BLE sync writes the new URLs and clears the issue.
    assert await manager.async_ble_sync(ADDRESS)
    written = fake_session.instances[0].written[0]
    assert written["settingsUrl"].endswith(
        "/api/paperlessoffline/new-token-xxxxxxxxxxxxxxxx/settings.json"
    )
    assert written["downloadUrl"].endswith("/new-token-xxxxxxxxxxxxxxxx/image.bmp")
    assert loaded_entry.data[CONF_PROVISIONED_TOKEN] == "new-token-xxxxxxxxxxxxxxxx"
    assert _issue(hass, ISSUE_REPROVISION, loaded_entry) is None


async def test_request_marks_provisioned(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry
) -> None:
    client = await hass_client_no_auth()
    await client.get(SETTINGS_URL)
    assert loaded_entry.data[CONF_PROVISIONED_TOKEN] == TOKEN
    # The test client comes from loopback, which a frame can't use: not recorded.
    assert loaded_entry.data[CONF_PROVISIONED_BASE] is None
    await client.get(SETTINGS_URL, headers={"Host": "192.168.1.10:8123"})
    assert loaded_entry.data[CONF_PROVISIONED_BASE] == "http://192.168.1.10:8123"


async def test_url_change_while_overdue(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer
) -> None:
    manager = loaded_entry.runtime_data
    client = await hass_client_no_auth()
    await client.get(SETTINGS_URL, headers={"Host": "192.168.1.10:8123"})
    assert loaded_entry.data[CONF_PROVISIONED_BASE] == "http://192.168.1.10:8123"
    hass.config.internal_url = "http://192.168.50.2:8123"
    await manager.async_refresh_base_url()
    assert _issue(hass, ISSUE_REPROVISION, loaded_entry) is None  # not overdue yet

    freezer.tick(timedelta(hours=4))
    await manager.async_refresh_base_url()
    issue = _issue(hass, ISSUE_REPROVISION, loaded_entry)
    assert issue is not None and issue.translation_key == "reprovision_url"
    assert _issue(hass, ISSUE_OFFLINE, loaded_entry) is None


async def _start_fix(hass_client, entry):
    client = await hass_client()
    resp = await client.post(
        "/api/repairs/issues/fix",
        json={"handler": DOMAIN, "issue_id": issue_id(ISSUE_REPROVISION, entry.entry_id)},
    )
    assert resp.status == 200, await resp.text()
    return client, await resp.json()


async def test_fix_flow_manual(hass: HomeAssistant, hass_client, loaded_entry) -> None:
    assert await async_setup_component(hass, "repairs", {})
    hass.config_entries.async_update_entry(
        loaded_entry, data={**loaded_entry.data, CONF_TOKEN: "rotated-token-xxxxxxxxxxxx"}
    )
    await hass.async_block_till_done()
    loaded_entry.runtime_data.async_update_issues()
    client, flow = await _start_fix(hass_client, loaded_entry)
    assert flow["step_id"] == "init"
    assert "rotated-token" in flow["description_placeholders"]["settings_url"]
    resp = await client.post(
        f"/api/repairs/issues/fix/{flow['flow_id']}", json={"method": "manual"}
    )
    assert (await resp.json())["type"] == "create_entry"
    assert _issue(hass, ISSUE_REPROVISION, loaded_entry) is None


async def test_fix_flow_bluetooth(
    hass: HomeAssistant, hass_client, loaded_entry, fake_session
) -> None:
    assert await async_setup_component(hass, "repairs", {})
    hass.config_entries.async_update_entry(
        loaded_entry, data={**loaded_entry.data, CONF_TOKEN: "rotated-token-xxxxxxxxxxxx"}
    )
    await hass.async_block_till_done()
    loaded_entry.runtime_data.async_update_issues()
    hass.config.components.add("bluetooth")
    info = MagicMock(address=ADDRESS)
    info.name = CLIENT_ID
    with patch(
        "homeassistant.components.bluetooth.async_discovered_service_info", return_value=[info]
    ):
        client, flow = await _start_fix(hass_client, loaded_entry)
        resp = await client.post(
            f"/api/repairs/issues/fix/{flow['flow_id']}", json={"method": "bluetooth"}
        )
    assert (await resp.json())["type"] == "create_entry"
    session = fake_session.instances[0]
    assert session.exited
    assert "rotated-token" in session.written[0]["settingsUrl"]
    assert _issue(hass, ISSUE_REPROVISION, loaded_entry) is None


async def test_fix_flow_bluetooth_not_found(hass: HomeAssistant, hass_client, loaded_entry) -> None:
    assert await async_setup_component(hass, "repairs", {})
    hass.config_entries.async_update_entry(
        loaded_entry, data={**loaded_entry.data, CONF_TOKEN: "rotated-token-xxxxxxxxxxxx"}
    )
    await hass.async_block_till_done()
    loaded_entry.runtime_data.async_update_issues()
    hass.config.components.add("bluetooth")
    with (
        patch("homeassistant.components.bluetooth.async_discovered_service_info", return_value=[]),
        patch(
            "homeassistant.components.bluetooth.async_process_advertisements",
            AsyncMock(side_effect=TimeoutError),
        ),
    ):
        client, flow = await _start_fix(hass_client, loaded_entry)
        resp = await client.post(
            f"/api/repairs/issues/fix/{flow['flow_id']}", json={"method": "bluetooth"}
        )
    result = await resp.json()
    assert result["errors"] == {"base": "not_found"}


async def test_migration_adds_provisioned_fields(hass: HomeAssistant) -> None:
    hass.config.internal_url = "http://192.168.1.10:8123"
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Old",
        unique_id="epd7-112233445566",
        version=1,
        minor_version=1,
        data={CONF_CLIENT_ID: "epd7-112233445566", CONF_PANEL: "epd7", CONF_TOKEN: "old-token-abc"},
        options={},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.minor_version == 2
    assert entry.data[CONF_PROVISIONED_TOKEN] == "old-token-abc"


async def test_base_url_replaces_mdns_host(hass: HomeAssistant) -> None:
    hass.config.internal_url = "http://homeassistant.local:8123"
    with patch(
        "homeassistant.components.network.async_get_source_ip",
        AsyncMock(return_value="192.168.1.20"),
    ):
        assert await async_frame_base_url(hass) == "http://192.168.1.20:8123"
    hass.config.internal_url = "http://10.0.0.5:8123"
    assert await async_frame_base_url(hass) == "http://10.0.0.5:8123"


async def test_unusable_provisioned_url_is_fixed_on_next_sync(
    hass: HomeAssistant, loaded_entry, fake_session
) -> None:
    """A loopback URL written to the frame earlier is replaced at the next button press."""
    manager = loaded_entry.runtime_data
    hass.config.internal_url = "http://192.168.1.10:8123"
    hass.config_entries.async_update_entry(
        loaded_entry,
        data={**loaded_entry.data, CONF_PROVISIONED_BASE: "http://127.0.0.1:8123"},
    )
    await manager.async_refresh_base_url()
    issue = _issue(hass, ISSUE_REPROVISION, loaded_entry)
    assert issue is not None and issue.translation_key == "reprovision_url"

    assert await manager.async_ble_sync(ADDRESS)
    assert (
        fake_session.instances[0].written[0]["settingsUrl"].startswith("http://192.168.1.10:8123/")
    )
    assert loaded_entry.data[CONF_PROVISIONED_BASE] == "http://192.168.1.10:8123"
    assert _issue(hass, ISSUE_REPROVISION, loaded_entry) is None


async def test_base_url_with_chosen_host(hass: HomeAssistant) -> None:
    hass.config.internal_url = "http://192.168.1.10:8123"
    assert await async_frame_base_url(hass, "10.0.0.7") == "http://10.0.0.7:8123"
    assert await async_frame_base_url(hass, "auto") == "http://192.168.1.10:8123"


async def test_ha_addresses(hass: HomeAssistant) -> None:
    from custom_components.paperlessoffline.urls import async_ha_addresses

    adapters = [
        {
            "name": "lo0",
            "enabled": False,
            "default": False,
            "ipv4": [{"address": "127.0.0.1", "network_prefix": 8}],
        },
        {
            "name": "eth1",
            "enabled": False,
            "default": False,
            "ipv4": [{"address": "10.0.0.7", "network_prefix": 24}],
        },
        {
            "name": "eth0",
            "enabled": True,
            "default": True,
            "ipv4": [{"address": "192.168.1.10", "network_prefix": 24}],
        },
    ]
    with patch(
        "homeassistant.components.network.async_get_adapters", AsyncMock(return_value=adapters)
    ):
        assert await async_ha_addresses(hass) == ["192.168.1.10", "10.0.0.7"]


def _options_input(**extra):
    return {
        "interval": 60,
        "order": "sequential",
        "mounting": "portrait",
        "quiet_hours": {
            "quiet_enabled": False,
            "quiet_start": "22:00:00",
            "quiet_end": "07:00:00",
            "quiet_suppress_motion": True,
        },
        "rendering": {
            "palette": "default",
            "dither": "default",
            "serpentine": "default",
            "fit": "default",
            "background": "default",
        },
        "authentication": {"auth_enabled": False},
        "ble_auto": True,
        "regenerate_token": False,
        **extra,
    }


async def test_options_choose_url_host(hass: HomeAssistant, loaded_entry, fake_session) -> None:
    manager = loaded_entry.runtime_data
    hass.config.internal_url = "http://192.168.1.10:8123"
    hass.config_entries.async_update_entry(
        loaded_entry, data={**loaded_entry.data, CONF_PROVISIONED_BASE: "http://192.168.1.10:8123"}
    )
    adapters = [
        {
            "name": "eth0",
            "enabled": True,
            "default": True,
            "ipv4": [{"address": "192.168.1.10", "network_prefix": 24}],
        },
        {
            "name": "eth1",
            "enabled": False,
            "default": False,
            "ipv4": [{"address": "10.0.0.7", "network_prefix": 24}],
        },
    ]
    with patch(
        "homeassistant.components.network.async_get_adapters", AsyncMock(return_value=adapters)
    ):
        result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
        schema_host = next(k for k in result["data_schema"].schema if str(k) == "url_host")
        options = result["data_schema"].schema[schema_host].config["options"]
        assert options == ["auto", "192.168.1.10", "10.0.0.7"]

        for bad, error in (
            ("http://x/", "invalid_host"),
            ("127.0.0.1", "unusable_host"),
            ("ha.local", "unusable_host"),
        ):
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], _options_input(url_host=bad)
            )
            assert result["errors"] == {"url_host": error}

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], _options_input(url_host="10.0.0.7")
        )
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert loaded_entry.options["url_host"] == "10.0.0.7"
    assert manager.base_url == "http://10.0.0.7:8123"
    # Explicit choice: the frame needs the new URLs right away.
    issue = _issue(hass, ISSUE_REPROVISION, loaded_entry)
    assert issue is not None and issue.translation_key == "reprovision_url"

    assert await manager.async_ble_sync(ADDRESS)
    assert fake_session.instances[0].written[0]["settingsUrl"].startswith("http://10.0.0.7:8123/")
    assert _issue(hass, ISSUE_REPROVISION, loaded_entry) is None


def _api(hass: HomeAssistant, port: int = 8123, ssl: bool = False) -> None:
    from homeassistant.components.http import ApiConfig

    hass.config.api = ApiConfig("192.168.1.20", "0.0.0.0", port, ssl)


@pytest.mark.parametrize(
    ("internal", "port", "ssl", "expected"),
    [
        # Used as configured, port kept whenever it isn't the default.
        ("http://192.168.1.10:8123", 8123, False, "http://192.168.1.10:8123"),
        ("http://ha.lan", 8123, False, "http://ha.lan"),  # e.g. a proxy on port 80
        ("https://ha.lan:8443", 8443, True, "https://ha.lan:8443"),
        # Unusable host: HA's own server at the LAN IP, with HA's real port.
        ("http://homeassistant.local", 8123, False, "http://192.168.1.20:8123"),
        ("http://127.0.0.1:8124", 8124, False, "http://192.168.1.20:8124"),
        ("http://localhost", 80, False, "http://192.168.1.20"),
        ("https://homeassistant.local", 8123, True, "https://192.168.1.20:8123"),
    ],
)
async def test_base_url_ports(hass: HomeAssistant, internal, port, ssl, expected) -> None:
    _api(hass, port, ssl)
    hass.config.internal_url = internal
    with patch(
        "homeassistant.components.network.async_get_source_ip",
        AsyncMock(return_value="192.168.1.20"),
    ):
        assert await async_frame_base_url(hass) == expected


async def test_chosen_host_uses_ha_port(hass: HomeAssistant) -> None:
    """A chosen address points at HA itself, even if the internal URL has no port."""
    _api(hass, 8123)
    hass.config.internal_url = "http://ha.lan"
    assert await async_frame_base_url(hass, "10.0.0.7") == "http://10.0.0.7:8123"
    _api(hass, 80)
    assert await async_frame_base_url(hass, "10.0.0.7") == "http://10.0.0.7"

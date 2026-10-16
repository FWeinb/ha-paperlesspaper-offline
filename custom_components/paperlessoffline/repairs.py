"""Fix flows for repair issues."""

from __future__ import annotations

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow, RepairsFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
import probatio as vol

from .data import DATA_KEY
from .frame import FrameManager
from .urls import frame_urls

BLE_WAIT_SECONDS = 45
METHOD_BLUETOOTH = "bluetooth"
METHOD_MANUAL = "manual"


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, str | int | float | None] | None
) -> RepairsFlow:
    """Create the fix flow for a reprovision issue."""
    entry_id = str((data or {}).get("entry_id", ""))
    manager = hass.data[DATA_KEY].entries.get(entry_id) if DATA_KEY in hass.data else None
    if manager is None:
        return ConfirmRepairFlow()
    return ReprovisionFlow(manager)


class ReprovisionFlow(RepairsFlow):
    """Give a frame HA's current URLs, over Bluetooth or by hand."""

    def __init__(self, manager: FrameManager) -> None:
        """Initialise."""
        self.manager = manager

    def _placeholders(self) -> dict[str, str]:
        base = self.manager.base_url
        urls = (
            frame_urls(base, self.manager.token)
            if base
            else {"image_url": "-", "settings_url": "-"}
        )
        return {"name": self.manager.display_name, **urls}

    async def async_step_init(self, user_input: dict[str, str] | None = None) -> RepairsFlowResult:
        """Ask how to update the frame."""
        errors: dict[str, str] = {}
        # The flow starts with the issue data as input; only "method" is an answer.
        if user_input is not None and "method" in user_input:
            if user_input["method"] == METHOD_MANUAL:
                self.manager.mark_provisioned(self.manager.base_url)
                self.manager.async_update_issues()
                return self.async_create_entry(data={})
            if self.manager.base_url is None:
                errors["base"] = "no_url"
            elif (error := await self._async_bluetooth()) is None:
                return self.async_create_entry(data={})
            else:
                errors["base"] = error
        has_ble = "bluetooth" in self.hass.config.components
        methods = [METHOD_BLUETOOTH, METHOD_MANUAL] if has_ble else [METHOD_MANUAL]
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "method", default=METHOD_BLUETOOTH if has_ble else METHOD_MANUAL
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=methods,
                            translation_key="reprovision_method",
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            errors=errors,
            description_placeholders=self._placeholders(),
        )

    async def _async_bluetooth(self) -> str | None:
        """Wait for the frame to advertise and write the URLs. Returns an error key."""
        if "bluetooth" not in self.hass.config.components:
            return "no_bluetooth"
        # Imported lazily so the integration works on systems without Bluetooth.
        from homeassistant.components import bluetooth  # noqa: PLC0415

        name = self.manager.client_id
        address = next(
            (
                info.address
                for info in bluetooth.async_discovered_service_info(self.hass, connectable=True)
                if info.name == name
            ),
            None,
        )
        if address is None:
            try:
                info = await bluetooth.async_process_advertisements(
                    self.hass,
                    lambda info: info.name == name,
                    bluetooth.BluetoothCallbackMatcher(local_name=name, connectable=True),
                    bluetooth.BluetoothScanningMode.ACTIVE,
                    BLE_WAIT_SECONDS,
                )
            except TimeoutError:
                return "not_found"
            address = info.address
        ok = await self.manager.async_ble_sync(address, exit_setup=True, force_provision=True)
        return None if ok else "ble_failed"

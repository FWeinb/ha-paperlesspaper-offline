"""Config and options flows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector
import probatio as vol

from .ble import FrameBleError, WifiConnectError, async_provision
from .const import (
    CLIENT_ID_RE,
    CONF_AUTH_ENABLED,
    CONF_AUTH_PASSWORD,
    CONF_AUTH_USER,
    CONF_BLE_AUTO,
    CONF_CLIENT_ID,
    CONF_INTERVAL,
    CONF_MOUNTING,
    CONF_ORDER,
    CONF_PANEL,
    CONF_PROVISIONED_BASE,
    CONF_PROVISIONED_TOKEN,
    CONF_QUIET_ENABLED,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_QUIET_SUPPRESS_MOTION,
    CONF_RENDER_DEFAULTS,
    CONF_TOKEN,
    CONF_URL_HOST,
    DEFAULT_INTERVAL,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DOMAIN,
    MAX_INTERVAL,
    MIN_INTERVAL,
    ORDER_SEQUENTIAL,
    ORDERS,
    PALETTES,
    PANELS,
)
from .frame import new_token
from .render import DITHER_METHODS, FIT_MODES, MOUNTINGS
from .render.pipeline import BACKGROUNDS
from .urls import (
    URL_HOST_AUTO,
    async_frame_base_url,
    async_ha_addresses,
    frame_can_use_host,
    frame_urls,
    valid_host,
)

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

CONF_NAME = "name"
CONF_PROVISION = "provision"
CONF_WIFI_SSID = "wifi_ssid"
CONF_WIFI_PASSWORD = "wifi_password"
SECTION_WIFI = "wifi"
CONF_REGENERATE = "regenerate_token"
SECTION_QUIET = "quiet_hours"
SECTION_AUTH = "authentication"
SECTION_RENDER = "rendering"
INHERIT = "default"


def _select(options: list[str] | tuple[str, ...], key: str) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=list(options),
            translation_key=key,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


async def _host_selector(hass: Any, current: str | None) -> selector.SelectSelector:
    """Choose "automatic", one of HA's IPv4 addresses, or type a host."""
    options = [URL_HOST_AUTO, *await async_ha_addresses(hass)]
    if current and current not in options:
        options.append(current)
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            custom_value=True,
            translation_key=CONF_URL_HOST,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _host_error(host: str | None) -> str | None:
    """Validate a chosen URL host; returns an error key."""
    host = (host or "").strip()
    if not host or host == URL_HOST_AUTO:
        return None
    if not valid_host(host):
        return "invalid_host"
    if not frame_can_use_host(host):
        return "unusable_host"
    return None


def _host_value(host: str | None) -> str | None:
    """Normalise a chosen host for storage (None = automatic)."""
    host = (host or "").strip()
    return None if not host or host == URL_HOST_AUTO else host


def initial_device_settings(urls: dict[str, str]) -> dict[str, object]:
    """Settings written over BLE when a frame is provisioned."""
    return {
        "settingsUrl": urls["settings_url"],
        "downloadUrl": urls["image_url"],
        "timeout": DEFAULT_INTERVAL,
        "httpAuthUser": "",
        "httpAuthPassword": "",
    }


class PaperlessConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a frame."""

    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        """Initialise."""
        self._client_id: str | None = None
        self._address: str | None = None
        self._name: str | None = None
        self._token = new_token()
        self._base_url: str | None = None
        self._url_host: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options flow."""
        return PaperlessOptionsFlow()

    def _entry_data(self) -> dict[str, Any]:
        assert self._client_id is not None
        return {
            CONF_CLIENT_ID: self._client_id,
            CONF_PANEL: self._client_id.split("-", 1)[0],
            CONF_TOKEN: self._token,
            # The frame is given (or shown) these, so remember them for repairs.
            CONF_PROVISIONED_TOKEN: self._token,
            CONF_PROVISIONED_BASE: self._base_url,
        }

    def _default_options(self) -> dict[str, Any]:
        assert self._client_id is not None
        panel = PANELS[self._client_id.split("-", 1)[0]]
        return {
            CONF_INTERVAL: DEFAULT_INTERVAL,
            CONF_ORDER: ORDER_SEQUENTIAL,
            CONF_MOUNTING: panel.default_mounting,
            CONF_URL_HOST: self._url_host or URL_HOST_AUTO,
        }

    def _create(self) -> ConfigFlowResult:
        return self.async_create_entry(
            title=self._name or str(self._client_id),
            data=self._entry_data(),
            options=self._default_options(),
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manual setup with the client id shown on the frame."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client_id = user_input[CONF_CLIENT_ID].strip().lower()
            if not CLIENT_ID_RE.match(client_id):
                errors[CONF_CLIENT_ID] = "invalid_client_id"
            elif host_error := _host_error(user_input.get(CONF_URL_HOST)):
                errors[CONF_URL_HOST] = host_error
            else:
                await self.async_set_unique_id(client_id)
                self._abort_if_unique_id_configured()
                self._url_host = _host_value(user_input.get(CONF_URL_HOST))
                if (base_url := await async_frame_base_url(self.hass, self._url_host)) is None:
                    return self.async_abort(reason="no_internal_url")
                self._base_url = base_url
                self._client_id = client_id
                self._name = user_input.get(CONF_NAME) or client_id
                return await self.async_step_urls()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_CLIENT_ID): str,
                        vol.Optional(CONF_NAME): str,
                        vol.Required(CONF_URL_HOST, default=URL_HOST_AUTO): await _host_selector(
                            self.hass, None
                        ),
                    }
                ),
                user_input,
            ),
            errors=errors,
        )

    async def async_step_urls(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the URLs to enter in the official web UI."""
        if user_input is not None:
            return self._create()
        assert self._base_url is not None
        return self.async_show_form(
            step_id="urls",
            description_placeholders=frame_urls(self._base_url, self._token),
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """A frame in setup mode was discovered."""
        client_id = (discovery_info.name or "").lower()
        if not CLIENT_ID_RE.match(client_id):
            return self.async_abort(reason="not_supported")
        await self.async_set_unique_id(client_id)
        self._abort_if_unique_id_configured()
        self._client_id = client_id
        self._address = discovery_info.address
        self.context["title_placeholders"] = {"name": client_id}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Name the frame, optionally set its WiFi, and write the URLs to it."""
        assert self._client_id is not None
        errors: dict[str, str] = {}
        if user_input is not None and (host_error := _host_error(user_input.get(CONF_URL_HOST))):
            errors[CONF_URL_HOST] = host_error
            user_input = {**user_input, "_invalid": True}
        if user_input is not None and "_invalid" not in user_input:
            self._url_host = _host_value(user_input.get(CONF_URL_HOST))
        if (base_url := await async_frame_base_url(self.hass, self._url_host)) is None:
            return self.async_abort(reason="no_internal_url")
        self._base_url = base_url
        if user_input is not None and "_invalid" not in user_input:
            self._name = user_input.get(CONF_NAME) or self._client_id
            if not user_input.get(CONF_PROVISION, True):
                return await self.async_step_urls()
            assert self._address is not None
            wifi_input = user_input.get(SECTION_WIFI) or {}
            ssid = (wifi_input.get(CONF_WIFI_SSID) or "").strip()
            wifi = (ssid, wifi_input.get(CONF_WIFI_PASSWORD) or "") if ssid else None
            try:
                await async_provision(
                    self.hass,
                    self._address,
                    initial_device_settings(frame_urls(base_url, self._token)),
                    wifi,
                )
            except WifiConnectError:
                errors["base"] = "wifi_failed"
            except FrameBleError:
                errors["base"] = "provision_failed"
            else:
                return self._create()
        suggested = dict(user_input or {CONF_NAME: self._client_id})
        suggested.pop("_invalid", None)
        if SECTION_WIFI in suggested:
            # Never echo the password back into the form.
            suggested[SECTION_WIFI] = {
                k: v for k, v in suggested[SECTION_WIFI].items() if k != CONF_WIFI_PASSWORD
            }
        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Optional(CONF_NAME): str,
                        vol.Required(CONF_URL_HOST, default=URL_HOST_AUTO): await _host_selector(
                            self.hass, self._url_host
                        ),
                        vol.Required(CONF_PROVISION, default=True): bool,
                        vol.Required(SECTION_WIFI): section(
                            vol.Schema(
                                {
                                    vol.Optional(CONF_WIFI_SSID): str,
                                    vol.Optional(CONF_WIFI_PASSWORD): selector.TextSelector(
                                        selector.TextSelectorConfig(
                                            type=selector.TextSelectorType.PASSWORD
                                        )
                                    ),
                                }
                            ),
                            {"collapsed": True},
                        ),
                    }
                ),
                suggested,
            ),
            description_placeholders={"client_id": self._client_id, "base_url": base_url},
            errors=errors,
        )


def _render_schema(current: dict[str, Any]) -> vol.Schema:
    def sel(key: str, options: tuple[str, ...]) -> dict[Any, Any]:
        return {
            vol.Required(key, default=current.get(key, INHERIT)): _select([INHERIT, *options], key)
        }

    serpentine = current.get("serpentine")
    fields: dict[Any, Any] = {
        **sel("palette", PALETTES),
        **sel("dither", DITHER_METHODS),
        vol.Required(
            "serpentine",
            default=INHERIT if serpentine is None else ("on" if serpentine else "off"),
        ): _select([INHERIT, "on", "off"], "serpentine"),
        **sel("fit", FIT_MODES),
        **sel("background", tuple(BACKGROUNDS)),
    }
    for key in ("brightness", "contrast", "saturation"):
        fields[vol.Optional(key, description={"suggested_value": current.get(key)})] = (
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=3, step=0.05, mode=selector.NumberSelectorMode.SLIDER
                )
            )
        )
    return vol.Schema(fields)


def _render_from_input(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("palette", "dither", "fit", "background"):
        if data.get(key, INHERIT) != INHERIT:
            out[key] = data[key]
    if data.get("serpentine", INHERIT) != INHERIT:
        out["serpentine"] = data["serpentine"] == "on"
    for key in ("brightness", "contrast", "saturation"):
        if data.get(key) is not None:
            out[key] = float(data[key])
    return out


class PaperlessOptionsFlow(OptionsFlow):
    """Frame settings."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Edit settings."""
        entry = self.config_entry
        opts = dict(entry.options)
        if user_input is not None:
            quiet = user_input[SECTION_QUIET]
            auth = user_input[SECTION_AUTH]
            errors: dict[str, str] = {}
            if auth.get(CONF_AUTH_ENABLED) and not (
                auth.get(CONF_AUTH_USER) and auth.get(CONF_AUTH_PASSWORD)
            ):
                errors["base"] = "auth_incomplete"
            if host_error := _host_error(user_input.get(CONF_URL_HOST)):
                errors[CONF_URL_HOST] = host_error
            if not errors:
                if user_input.get(CONF_REGENERATE):
                    self.hass.config_entries.async_update_entry(
                        entry, data={**entry.data, CONF_TOKEN: new_token()}
                    )
                new = {
                    **opts,
                    CONF_INTERVAL: int(user_input[CONF_INTERVAL]) * 60,
                    CONF_ORDER: user_input[CONF_ORDER],
                    CONF_MOUNTING: user_input[CONF_MOUNTING],
                    CONF_QUIET_ENABLED: quiet[CONF_QUIET_ENABLED],
                    CONF_QUIET_START: quiet[CONF_QUIET_START],
                    CONF_QUIET_END: quiet[CONF_QUIET_END],
                    CONF_QUIET_SUPPRESS_MOTION: quiet[CONF_QUIET_SUPPRESS_MOTION],
                    CONF_AUTH_ENABLED: auth[CONF_AUTH_ENABLED],
                    CONF_AUTH_USER: auth.get(CONF_AUTH_USER, ""),
                    CONF_AUTH_PASSWORD: auth.get(CONF_AUTH_PASSWORD, ""),
                    CONF_RENDER_DEFAULTS: _render_from_input(user_input[SECTION_RENDER]),
                    CONF_BLE_AUTO: user_input[CONF_BLE_AUTO],
                    CONF_URL_HOST: _host_value(user_input.get(CONF_URL_HOST)) or URL_HOST_AUTO,
                }
                return self.async_create_entry(data=new)
        else:
            errors = {}

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_INTERVAL, default=opts.get(CONF_INTERVAL, DEFAULT_INTERVAL) // 60
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_INTERVAL // 60,
                        max=MAX_INTERVAL // 60,
                        step=1,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(CONF_ORDER, default=opts.get(CONF_ORDER, ORDER_SEQUENTIAL)): _select(
                    ORDERS, CONF_ORDER
                ),
                vol.Required(CONF_MOUNTING, default=opts.get(CONF_MOUNTING, MOUNTINGS[0])): _select(
                    MOUNTINGS, CONF_MOUNTING
                ),
                vol.Required(SECTION_QUIET): section(
                    vol.Schema(
                        {
                            vol.Required(
                                CONF_QUIET_ENABLED, default=opts.get(CONF_QUIET_ENABLED, False)
                            ): bool,
                            vol.Required(
                                CONF_QUIET_START,
                                default=opts.get(CONF_QUIET_START, DEFAULT_QUIET_START),
                            ): selector.TimeSelector(),
                            vol.Required(
                                CONF_QUIET_END,
                                default=opts.get(CONF_QUIET_END, DEFAULT_QUIET_END),
                            ): selector.TimeSelector(),
                            vol.Required(
                                CONF_QUIET_SUPPRESS_MOTION,
                                default=opts.get(CONF_QUIET_SUPPRESS_MOTION, True),
                            ): bool,
                        }
                    ),
                    {"collapsed": not opts.get(CONF_QUIET_ENABLED, False)},
                ),
                vol.Required(SECTION_RENDER): section(
                    _render_schema(opts.get(CONF_RENDER_DEFAULTS, {})), {"collapsed": True}
                ),
                vol.Required(SECTION_AUTH): section(
                    vol.Schema(
                        {
                            vol.Required(
                                CONF_AUTH_ENABLED, default=opts.get(CONF_AUTH_ENABLED, False)
                            ): bool,
                            vol.Optional(
                                CONF_AUTH_USER,
                                description={"suggested_value": opts.get(CONF_AUTH_USER)},
                            ): str,
                            vol.Optional(
                                CONF_AUTH_PASSWORD,
                                description={"suggested_value": opts.get(CONF_AUTH_PASSWORD)},
                            ): selector.TextSelector(
                                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                            ),
                        }
                    ),
                    {"collapsed": True},
                ),
                vol.Required(
                    CONF_URL_HOST, default=opts.get(CONF_URL_HOST) or URL_HOST_AUTO
                ): await _host_selector(self.hass, opts.get(CONF_URL_HOST)),
                vol.Required(CONF_BLE_AUTO, default=opts.get(CONF_BLE_AUTO, True)): bool,
                vol.Required(CONF_REGENERATE, default=False): bool,
            }
        )
        current_host = _host_value(opts.get(CONF_URL_HOST))
        base_url = await async_frame_base_url(self.hass, current_host)
        urls = (
            frame_urls(base_url, entry.data[CONF_TOKEN])
            if base_url
            else {"image_url": "-", "settings_url": "-"}
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors, description_placeholders=urls
        )

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
from homeassistant.helpers.network import NoURLAvailableError, get_url
import probatio as vol

from .ble import FrameBleError, async_provision
from .const import (
    CLIENT_ID_RE,
    CONF_AUTH_ENABLED,
    CONF_AUTH_PASSWORD,
    CONF_AUTH_USER,
    CONF_CLIENT_ID,
    CONF_INTERVAL,
    CONF_MOUNTING,
    CONF_ORDER,
    CONF_PANEL,
    CONF_QUIET_ENABLED,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_QUIET_SUPPRESS_MOTION,
    CONF_RENDER_DEFAULTS,
    CONF_TOKEN,
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
from .frame import IMAGE_PATH, SETTINGS_PATH, new_token
from .render import DITHER_METHODS, FIT_MODES, MOUNTINGS
from .render.pipeline import BACKGROUNDS

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

CONF_NAME = "name"
CONF_PROVISION = "provision"
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


def _base_url(hass: Any) -> str:
    return get_url(hass, allow_external=False, allow_cloud=False, prefer_external=False)


def frame_urls(base_url: str, token: str) -> dict[str, str]:
    """Image and settings URLs for a token."""
    return {
        "image_url": base_url + IMAGE_PATH.format(token=token),
        "settings_url": base_url + SETTINGS_PATH.format(token=token),
    }


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

    def __init__(self) -> None:
        """Initialise."""
        self._client_id: str | None = None
        self._address: str | None = None
        self._name: str | None = None
        self._token = new_token()

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
        }

    def _default_options(self) -> dict[str, Any]:
        assert self._client_id is not None
        panel = PANELS[self._client_id.split("-", 1)[0]]
        return {
            CONF_INTERVAL: DEFAULT_INTERVAL,
            CONF_ORDER: ORDER_SEQUENTIAL,
            CONF_MOUNTING: panel.default_mounting,
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
            else:
                await self.async_set_unique_id(client_id)
                self._abort_if_unique_id_configured()
                try:
                    _base_url(self.hass)
                except NoURLAvailableError:
                    return self.async_abort(reason="no_internal_url")
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
        return self.async_show_form(
            step_id="urls",
            description_placeholders=frame_urls(_base_url(self.hass), self._token),
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
        """Name the frame and write the URLs to it."""
        assert self._client_id is not None
        errors: dict[str, str] = {}
        try:
            base_url = _base_url(self.hass)
        except NoURLAvailableError:
            return self.async_abort(reason="no_internal_url")
        if user_input is not None:
            self._name = user_input.get(CONF_NAME) or self._client_id
            if not user_input.get(CONF_PROVISION, True):
                return await self.async_step_urls()
            assert self._address is not None
            try:
                await async_provision(
                    self.hass,
                    self._address,
                    initial_device_settings(frame_urls(base_url, self._token)),
                )
            except FrameBleError:
                errors["base"] = "provision_failed"
            else:
                return self._create()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Optional(CONF_NAME): str,
                        vol.Required(CONF_PROVISION, default=True): bool,
                    }
                ),
                user_input or {CONF_NAME: self._client_id},
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
                vol.Required(CONF_REGENERATE, default=False): bool,
            }
        )
        try:
            urls = frame_urls(_base_url(self.hass), entry.data[CONF_TOKEN])
        except NoURLAvailableError:
            urls = {"image_url": "-", "settings_url": "-"}
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors, description_placeholders=urls
        )

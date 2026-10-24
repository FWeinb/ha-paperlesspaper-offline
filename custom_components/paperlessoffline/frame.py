"""Per-frame runtime: library, slideshow, rendering and request handling."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
from dataclasses import asdict, replace
from datetime import datetime
import hashlib
import json
import logging
import math
from pathlib import Path
import secrets
import time
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, TemplateError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util
from yarl import URL

from . import housekeeping, slideshow
from .ble import FrameBleError, FrameSession
from .cache import RenderCache, cache_key
from .cards import (
    BACKGROUND_PHOTO,
    CARD_BACKGROUNDS,
    copy_overlays,
    preset_name,
    preset_overlays,
    text_color_on,
)
from .const import (
    ALLOWED_FORMATS,
    BLE_COOLDOWN_SECONDS,
    CONF_AUTH_ENABLED,
    CONF_AUTH_PASSWORD,
    CONF_AUTH_USER,
    CONF_AUTO_ROTATION,
    CONF_BLE_AUTO,
    CONF_CHARGER_MODE,
    CONF_CLIENT_ID,
    CONF_INTERVAL,
    CONF_MOTION_WAKEUP,
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
    CONF_TELEMETRY,
    CONF_TOKEN,
    CONF_URL_HOST,
    DEFAULT_INTERVAL,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DOMAIN,
    EVENT_FRAME_WAKE,
    IMAGE_PATH,
    MAX_IMAGE_PIXELS,
    MAX_UPLOAD_BYTES,
    ORDER_SEQUENTIAL,
    PANELS,
    SETTINGS_GRACE_SECONDS,
    SETTINGS_PATH,
    STORAGE_DIR,
    WAKE_DEBOUNCE_SECONDS,
    PanelSpec,
)
from .exif import read_capture
from .issues import async_update_issues, reprovision_reason
from .render import (
    Canvas,
    OverlayStyle,
    PlaceholderText,
    RenderOptions,
    RenderResult,
    TooManyPixelsError,
    canvas_for,
    composite,
    make_thumbnail,
    render,
    render_fill,
    render_placeholder,
    render_preview,
    validate_image,
)
from .schedule import parse_time, quiet_change, quiet_sleep
from .settings import resolve
from .store import KIND_CARD, FrameState, FrameStore, GlobalStore, LibraryItem, OverlayDef, Override
from .templates import is_truthy, photo_vars, render_text, template_variables
from .urls import URL_HOST_AUTO, async_frame_base_url, frame_can_use_host, frame_urls

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

MAX_TELEMETRY_KEYS = 16
MAX_FW_LENGTH = 32


def parse_wake_status(query: dict[str, str]) -> dict[str, Any]:
    """Pick the firmware's telemetry values out of an image request, ignoring bad ones."""
    status: dict[str, Any] = {}
    with contextlib.suppress(KeyError, ValueError):
        status["voltage"] = int(query["voltage"])
    for key in ("usb", "charging"):
        if query.get(key) in ("0", "1"):
            status[key] = query[key] == "1"
    if query.get("orientation") in ("0", "1", "2", "3"):
        status["orientation"] = int(query["orientation"])
    return status


def signal_update(entry_id: str) -> str:
    """Dispatcher signal fired whenever a frame's state changes."""
    return f"{DOMAIN}_{entry_id}_update"


SIGNAL_ANY_UPDATE = f"{DOMAIN}_any_update"
PLACEHOLDER_NAME = "placeholder"
THUMB_SIZES = (320, 1280)


def new_token() -> str:
    """Return a new unguessable URL token."""
    return secrets.token_urlsafe(24)


def _hash(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


class FrameManager:
    """Everything HA knows and does for one frame."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, global_store: GlobalStore) -> None:
        """Initialise."""
        self.hass = hass
        self.entry = entry
        self.global_store = global_store
        self.client_id: str = entry.data[CONF_CLIENT_ID]
        self.panel: PanelSpec = PANELS[entry.data[CONF_PANEL]]
        self.store = FrameStore(hass, entry.entry_id)
        self.directory = Path(hass.config.path(STORAGE_DIR, entry.entry_id))
        self.originals = self.directory / "originals"
        self.cache = RenderCache(self.directory / "cache")
        self._lock = asyncio.Lock()
        self._render_lock = asyncio.Lock()
        self._prerender_task: asyncio.Task[None] | None = None
        self._ble_task: asyncio.Task[bool] | None = None
        self._unsub_quiet: CALLBACK_TYPE | None = None
        self._ble_last_attempt = 0.0
        # HA's URL as the frame should use it; refreshed periodically.
        self.base_url: str | None = None

    # ------------------------------------------------------------------ setup

    async def async_setup(self) -> None:
        """Load state and prepare directories."""
        await self.store.async_load()
        await self.hass.async_add_executor_job(self._make_dirs)
        await self._async_read_missing_exif()
        self.base_url = await async_frame_base_url(self.hass, self.url_host)

    async def _async_read_missing_exif(self) -> None:
        """One-time migration: fill in capture data of photos added before it existed."""
        todo = [p for p in self.photos if not p.exif_read and not p.is_card]
        if not todo:
            return
        zone = dt_util.get_default_time_zone()
        results = await self.hass.async_add_executor_job(
            lambda: [read_capture(self.originals / p.filename, zone) for p in todo]
        )
        for photo, (date, location) in zip(todo, results, strict=True):
            photo.date, photo.location, photo.exif_read = date, location, True
        self.store.schedule_save()

    def _make_dirs(self) -> None:
        self.originals.mkdir(parents=True, exist_ok=True)
        self.cache.directory.mkdir(parents=True, exist_ok=True)

    async def async_unload(self) -> None:
        """Flush state."""
        if self._prerender_task:
            self._prerender_task.cancel()
        if self._ble_task:
            self._ble_task.cancel()
        self._cancel_quiet_timer()
        await self.store.async_save()

    # ------------------------------------------------------------ properties

    @property
    def token(self) -> str:
        """URL token."""
        return str(self.entry.data[CONF_TOKEN])

    @property
    def options(self) -> dict[str, Any]:
        """Entry options."""
        return dict(self.entry.options)

    @property
    def state(self) -> FrameState:
        """Persistent runtime state."""
        return self.store.state

    @property
    def photos(self) -> list[LibraryItem]:
        """Library, in rotation order."""
        return self.store.photos

    @property
    def canvas(self) -> Canvas:
        """Canvas for the configured mounting."""
        return canvas_for(
            self.panel.width,
            self.panel.height,
            self.options.get(CONF_MOUNTING, self.default_mounting),
        )

    @property
    def default_mounting(self) -> str:
        """How this panel type is usually hung."""
        return self.panel.default_mounting

    @property
    def order(self) -> str:
        """Slideshow order."""
        return str(self.options.get(CONF_ORDER, ORDER_SEQUENTIAL))

    @property
    def interval(self) -> int:
        """Base refresh interval (s)."""
        return int(self.options.get(CONF_INTERVAL, DEFAULT_INTERVAL))

    @property
    def device_id(self) -> str | None:
        """Device registry id."""
        device = self._device()
        return device.id if device else None

    def _device(self) -> dr.DeviceEntry | None:
        return dr.async_get(self.hass).async_get_device_by_identifier(
            (DOMAIN, self.client_id), self.entry.entry_id
        )

    @property
    def display_name(self) -> str:
        """The frame's name as the user sees it: a device rename wins over the entry title."""
        device = self._device()
        if device is not None and (device.name_by_user or device.name):
            return str(device.name_by_user or device.name)
        return self.entry.title

    def image_path(self) -> str:
        """Path of the image endpoint."""
        return IMAGE_PATH.format(token=self.token)

    def settings_path(self) -> str:
        """Path of the settings endpoint."""
        return SETTINGS_PATH.format(token=self.token)

    def get_photo(self, photo_id: str | None) -> LibraryItem | None:
        """Look up a photo by id."""
        return next((p for p in self.photos if p.id == photo_id), None)

    def require_photo(self, photo_id: str) -> LibraryItem:
        """Look up a photo or raise a validation error."""
        if (photo := self.get_photo(photo_id)) is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="photo_not_found",
                translation_placeholders={"photo_id": photo_id},
            )
        return photo

    def enabled_ids(self) -> list[str]:
        """Ids of photos in the rotation, in order."""
        return [p.id for p in self.photos if p.enabled]

    # --------------------------------------------------------------- notify

    @callback
    def _changed(self, prerender: bool = True) -> None:
        self.store.schedule_save()
        async_dispatcher_send(self.hass, signal_update(self.entry.entry_id))
        async_dispatcher_send(self.hass, SIGNAL_ANY_UPDATE, self.entry.entry_id)
        if prerender:
            self._schedule_prerender()

    @callback
    def async_options_updated(self) -> None:
        """Handle changed entry options/global defaults."""
        self._schedule_quiet_timer()
        self._changed()

    @callback
    def _schedule_quiet_timer(self) -> None:
        """Update entities when quiet hours start or stop suppressing motion."""
        self._cancel_quiet_timer()
        _, change = self.motion_quiet_hours(dt_util.utcnow())
        if change is not None:
            self._unsub_quiet = async_track_point_in_utc_time(
                self.hass, self._quiet_hours_changed, change
            )

    @callback
    def _quiet_hours_changed(self, _now: datetime) -> None:
        self._unsub_quiet = None
        self._schedule_quiet_timer()
        self._changed(prerender=False)

    @callback
    def _cancel_quiet_timer(self) -> None:
        if self._unsub_quiet is not None:
            self._unsub_quiet()
            self._unsub_quiet = None

    # ------------------------------------------------------------ slideshow

    def override_pending(self) -> bool:
        """Whether a one-off image is waiting to be (or still being) shown."""
        ov = self.state.override
        return ov is not None and (ov.wakes_remaining is None or ov.wakes_remaining > 0)

    def up_next(self) -> tuple[str, str | None]:
        """Return (kind, photo id) the frame will show on its next wake."""
        if self.override_pending():
            return "override", None
        photo_id, bag = slideshow.peek(
            self.order,
            self.enabled_ids(),
            self.state.current_id,
            self.state.queued_id,
            self.state.bag,
        )
        self.state.bag = bag
        if photo_id is None:
            return "placeholder", None
        return "photo", photo_id

    def _advance(self) -> None:
        """Move to the next item; called once per wake."""
        st = self.state
        if st.override is not None and not self.override_pending():
            st.override = None
        if self.override_pending():
            assert st.override is not None
            if st.override.wakes_remaining is not None:
                st.override.wakes_remaining -= 1
            st.override.shown += 1
            st.current_kind = "override"
            return
        kind, photo_id = self.up_next()
        if kind == "placeholder":
            st.current_kind = "placeholder"
            st.current_id = None
            return
        if st.queued_id == photo_id:
            st.queued_id = None
        elif self.order != ORDER_SEQUENTIAL and st.bag and st.bag[0] == photo_id:
            st.bag = st.bag[1:]
        st.current_kind = "photo"
        st.current_id = photo_id

    @callback
    def async_queue_photo(self, photo_id: str) -> None:
        """Show a specific photo on the next wake."""
        self.require_photo(photo_id)
        self.state.queued_id = photo_id
        self._changed()

    @callback
    def async_skip(self) -> None:
        """Skip the photo that would be shown next."""
        kind, photo_id = self.up_next()
        if kind != "photo" or photo_id is None:
            return
        st = self.state
        if self.order == ORDER_SEQUENTIAL:
            st.queued_id = slideshow.next_sequential(self.enabled_ids(), photo_id)
        elif st.queued_id == photo_id:
            st.queued_id = None
        elif st.bag and st.bag[0] == photo_id:
            st.bag = st.bag[1:]
        self._changed()

    # ------------------------------------------------------------- requests

    def _register_request(self, query: dict[str, str], kind: str) -> bool:
        """Record a request; returns True if it starts a new wake.

        The firmware fetches the settings JSON exactly once per wake, before the
        image, so a settings request always starts a wake. Image requests are
        made twice per wake (redirect probe + download) plus retries; they only
        start a wake for frames that don't fetch settings, debounced by time.
        """
        now = time.time()
        st = self.state
        if kind == "settings":
            is_wake = True
        else:
            sleep = st.last_timeout or self.interval
            uses_settings = (
                st.last_settings_fetch is not None
                and now - st.last_settings_fetch < 2 * sleep + SETTINGS_GRACE_SECONDS
            )
            is_wake = not uses_settings and (
                st.last_request is None or now - st.last_request > WAKE_DEBOUNCE_SECONDS
            )
        st.last_request = now
        if query:
            for key, value in list(query.items())[:MAX_TELEMETRY_KEYS]:
                st.telemetry[key[:32]] = value[:64]
            if kind == "image":
                self._register_telemetry(query, now)
        if is_wake:
            st.last_wake = now
            st.wake_count += 1
            self._advance()
            self._evaluate_overlays_for_wake()
            self._fire_wake()
        return is_wake

    def _register_telemetry(self, query: dict[str, str], now: float) -> None:
        """Take battery, power, orientation and firmware version from an image request."""
        st = self.state
        if status := parse_wake_status(query):
            st.wake_status.update(status)
            st.wake_read_at.update(dict.fromkeys(status, now))
        fw = query.get("fw", "")[:MAX_FW_LENGTH]
        if fw and fw != st.fw:
            st.fw = fw
            if device := self._device():
                dr.async_get(self.hass).async_update_device(device.id, sw_version=fw)

    def status_reading(self, key: str) -> tuple[Any, str, float] | None:
        """Newest ``(value, source, read_at)`` of a status key from wake or Bluetooth."""
        st = self.state
        found = []
        if key in st.ble_status and st.ble_read_at is not None:
            found.append((st.ble_read_at, "bluetooth", st.ble_status[key]))
        if key in st.wake_status and key in st.wake_read_at:
            found.append((st.wake_read_at[key], "wake", st.wake_status[key]))
        if not found:
            return None
        read_at, source, value = max(found, key=lambda r: r[0])
        return value, source, read_at

    @callback
    def _fire_wake(self) -> None:
        st = self.state
        photo = self.get_photo(st.current_id) if st.current_kind == "photo" else None
        self.hass.bus.async_fire(
            EVENT_FRAME_WAKE,
            {
                "config_entry_id": self.entry.entry_id,
                "device_id": self.device_id,
                "client_id": self.client_id,
                "kind": st.current_kind,
                "photo_id": photo.id if photo else None,
                "photo_name": photo.name if photo else None,
                "wake_count": st.wake_count,
            },
        )

    async def async_handle_image_request(
        self, query: dict[str, str], origin: str | None = None
    ) -> tuple[bytes, datetime]:
        """Return (bmp, last-modified) for the frame's image request."""
        async with self._lock:
            self._register_request(query, "image")
            self._note_origin(origin)
            key, name, fresh = await self._async_current_render()
            st = self.state
            if fresh:
                # A freshly rendered base: draw this wake's overlays on top.
                st.served_base_key = key
                shown = self.get_photo(st.current_id) if st.current_kind == "photo" else None
                draw = self._overlay_draw_list(
                    self._applicable_overlays(st.current_kind, shown), st.overlay_texts
                )
                if draw:
                    key = await self._async_render_composite(key, draw)
            bmp = await self.hass.async_add_executor_job(self.cache.read_bmp, key)
            if bmp is None:
                raise HomeAssistantError("Rendered image disappeared")
            if key != st.served_key:
                st.served_lm = max(int(time.time()), st.served_lm + 1)
                st.served_key = key
                st.served_name = name
            self._changed()
            return bmp, dt_util.utc_from_timestamp(st.served_lm)

    async def _async_current_render(self) -> tuple[str, str, bool]:
        """Render (or fetch) what should be on screen now.

        Returns (key, name, fresh); ``fresh`` is False when the frame keeps the
        image it already has (which already includes its overlays).
        """
        st = self.state
        if st.current_kind == "override" and st.override is not None:
            return await self._async_render_override(st.override), st.override.name, True
        if st.current_kind == "photo":
            if photo := self.get_photo(st.current_id):
                return await self.async_render_photo(photo), photo.name, True
            if await self._async_served_available():
                # Deleted since the wake: keep what the frame already shows.
                return str(st.served_key), st.served_name or "", False
            self._advance()
            self._evaluate_overlays_for_wake()
            if st.current_kind == "photo" and (photo := self.get_photo(st.current_id)):
                return await self.async_render_photo(photo), photo.name, True
        # Empty rotation: keep the last photo, or show the (current) placeholder.
        if st.served_name != PLACEHOLDER_NAME and await self._async_served_available():
            return str(st.served_key), st.served_name or "", False
        return await self._async_render_placeholder(), PLACEHOLDER_NAME, True

    async def _async_served_available(self) -> bool:
        key = self.state.served_key
        return key is not None and await self.hass.async_add_executor_job(self.cache.has, key)

    def device_settings(self, download_url: str | None) -> dict[str, Any]:
        """Settings as the user configured them (before quiet-hour adjustment)."""
        opts = self.options
        auth = bool(opts.get(CONF_AUTH_ENABLED))
        data: dict[str, Any] = {
            "timeout": self.interval,
            "motionWakeup": bool(opts.get(CONF_MOTION_WAKEUP, False)),
            "chargerMode": bool(opts.get(CONF_CHARGER_MODE, False)),
            "autoRotation": bool(opts.get(CONF_AUTO_ROTATION, False)),
            "telemetry": bool(opts.get(CONF_TELEMETRY, True)),
            "httpAuthUser": opts.get(CONF_AUTH_USER, "") if auth else "",
            "httpAuthPassword": opts.get(CONF_AUTH_PASSWORD, "") if auth else "",
        }
        if download_url:
            data["downloadUrl"] = download_url
        return data

    def device_settings_hash(self) -> str:
        """Hash of the user-controlled settings (not quiet-hour adjustments)."""
        return _hash(self.device_settings(None))

    def effective_settings(self, download_url: str | None, now: datetime) -> dict[str, Any]:
        """Settings to send right now, with quiet hours applied."""
        data = self.device_settings(download_url)
        opts = self.options
        if opts.get(CONF_QUIET_ENABLED):
            sleep = quiet_sleep(
                dt_util.as_local(now),
                parse_time(opts.get(CONF_QUIET_START, DEFAULT_QUIET_START)),
                parse_time(opts.get(CONF_QUIET_END, DEFAULT_QUIET_END)),
            )
            if sleep is not None:
                data["timeout"] = max(sleep, 60)
                if opts.get(CONF_QUIET_SUPPRESS_MOTION, True):
                    data["motionWakeup"] = False
        return data

    def motion_quiet_hours(self, now: datetime) -> tuple[datetime | None, datetime | None]:
        """When quiet hours stop turning motion wake-up off, and when to check again.

        The first is None unless quiet hours suppress motion right now; the
        second is None when quiet hours never do.
        """
        opts = self.options
        if not (opts.get(CONF_QUIET_ENABLED) and opts.get(CONF_QUIET_SUPPRESS_MOTION, True)):
            return None, None
        inside, change = quiet_change(
            dt_util.as_local(now),
            parse_time(opts.get(CONF_QUIET_START, DEFAULT_QUIET_START)),
            parse_time(opts.get(CONF_QUIET_END, DEFAULT_QUIET_END)),
        )
        return (change if inside else None), change

    def motion_suppressed_until(self, now: datetime) -> datetime | None:
        """End of quiet hours if they turn the enabled motion wake-up off right now."""
        if not self.options.get(CONF_MOTION_WAKEUP, False):
            return None
        return self.motion_quiet_hours(now)[0]

    async def async_handle_settings_request(
        self,
        query: dict[str, str],
        download_url: str,
        if_modified_since: str | None,
        origin: str | None = None,
    ) -> tuple[dict[str, Any] | None, datetime]:
        """Return (settings or None for 304, last-modified)."""
        async with self._lock:
            self._register_request(query, "settings")
            self._note_origin(origin)
            payload = self.effective_settings(download_url, dt_util.utcnow())
            st = self.state
            digest = _hash(payload)
            if digest != st.settings_hash:
                st.settings_hash = digest
                st.settings_lm = max(int(time.time()), st.settings_lm + 1)
            st.fetched_device_hash = self.device_settings_hash()
            st.served_motion_wakeup = bool(payload["motionWakeup"])
            st.last_settings_fetch = time.time()
            st.last_timeout = int(payload["timeout"])
            self._changed()
            last_modified = dt_util.utc_from_timestamp(st.settings_lm)
        if if_modified_since and if_modified_since.strip() == http_date(last_modified):
            return None, last_modified
        return payload, last_modified

    # ------------------------------------------------- provisioning / repairs

    @callback
    def _note_origin(self, origin: str | None) -> None:
        """A request with our token arrived: the frame has working URLs."""
        host = URL(origin).host if origin else None
        # Behind a local reverse proxy the origin can be loopback; don't record that.
        self.mark_provisioned(origin if host and frame_can_use_host(host) else None)
        self.async_update_issues()

    @callback
    def mark_provisioned(self, base_url: str | None) -> None:
        """Record which base URL and token the frame is known to use."""
        data = self.entry.data
        new = {**data, CONF_PROVISIONED_TOKEN: self.token}
        if base_url:
            new[CONF_PROVISIONED_BASE] = base_url
        if new != dict(data):
            self.hass.config_entries.async_update_entry(self.entry, data=new)

    @property
    def url_host(self) -> str | None:
        """Host chosen for the frame's URLs, or None for automatic."""
        host = self.options.get(CONF_URL_HOST)
        return None if not host or host == URL_HOST_AUTO else str(host)

    async def async_refresh_base_url(self) -> None:
        """Re-evaluate HA's local URL and the repair issues."""
        self.base_url = await async_frame_base_url(self.hass, self.url_host)
        self.async_update_issues()

    @callback
    def async_update_issues(self) -> None:
        """Create or clear repair issues for this frame."""
        async_update_issues(self.hass, self, self.base_url)

    def needs_reprovision(self) -> bool:
        """Whether the frame should be given new URLs."""
        return reprovision_reason(self, self.base_url) is not None

    def provision_settings(self, base_url: str) -> dict[str, Any]:
        """Everything to write over BLE so the frame uses ``base_url``."""
        urls = frame_urls(base_url, self.token)
        data = self.effective_settings(urls["image_url"], dt_util.utcnow())
        data["settingsUrl"] = urls["settings_url"]
        return data

    # ------------------------------------------------------------------ BLE

    @callback
    def async_ble_seen(self, address: str) -> None:
        """The frame is advertising (setup mode): read status, push changes."""
        if not self.options.get(CONF_BLE_AUTO, True):
            return
        if self._ble_task and not self._ble_task.done():
            return
        now = time.time()
        if now - self._ble_last_attempt < BLE_COOLDOWN_SECONDS:
            return
        self._ble_last_attempt = now
        self._ble_task = self.hass.async_create_background_task(
            self.async_ble_sync(address), f"{DOMAIN} ble {self.client_id}"
        )

    async def async_ble_sync(
        self, address: str, *, exit_setup: bool = False, force_provision: bool = False
    ) -> bool:
        """Connect, read status and write pending settings / new URLs.

        Returns True if the frame now has HA's current settings.
        """
        st = self.state
        reprovision = (force_provision or self.needs_reprovision()) and self.base_url is not None
        pending = self.settings_pending()
        written = False
        try:
            async with FrameSession(self.hass, address) as session:
                st.ble_status = await session.read_status()
                st.ble_read_at = time.time()
                if reprovision or pending:
                    if reprovision and self.base_url:
                        settings = self.provision_settings(self.base_url)
                    else:
                        settings = self.effective_settings(None, dt_util.utcnow())
                    await session.write_settings(settings)
                    await session.save()
                    st.served_motion_wakeup = bool(settings["motionWakeup"])
                    written = True
                if exit_setup:
                    await session.exit_setup()
        except FrameBleError as err:
            _LOGGER.debug("Bluetooth sync with %s failed: %s", self.client_id, err)
            st.ble_error = str(err)
            self._changed(prerender=False)
            return False
        st.ble_error = None
        if written:
            st.fetched_device_hash = self.device_settings_hash()
            if reprovision:
                self.mark_provisioned(self.base_url)
        self._changed(prerender=False)
        self.async_update_issues()
        return True

    # ---------------------------------------------------------------- status

    def settings_pending(self) -> bool:
        """Whether the frame's settings differ from what it should have now.

        Besides the user's settings this covers quiet hours turning motion
        wake-up off or on again, which the frame only learns when it fetches.
        """
        st = self.state
        if st.fetched_device_hash != self.device_settings_hash():
            return True
        if st.served_motion_wakeup is None:
            return False
        now = self.effective_settings(None, dt_util.utcnow())["motionWakeup"]
        return st.served_motion_wakeup != now

    def pending_changes(self) -> list[str]:
        """What the frame hasn't picked up yet."""
        pending = []
        eval_base = self.state.overlay_eval_base or ""
        shown = self._current_photo()
        has_overlays = bool(self.overlays or (shown and shown.overlays))
        if has_overlays and not eval_base.endswith("|" + self.overlay_defs_hash(shown)):
            pending.append("overlays")
        if self.settings_pending():
            pending.append("settings")
        if self.state.queued_id and self.get_photo(self.state.queued_id):
            pending.append("photo")
        ov = self.state.override
        if ov is not None and ov.shown == 0:
            pending.append("image")
        st = self.state
        if (
            st.served_name == PLACEHOLDER_NAME
            and st.served_key != self.placeholder_key()
            and self.up_next()[0] == "placeholder"
        ):
            # e.g. the frame was renamed while showing "No photos yet".
            pending.append("placeholder")
        return pending

    # ------------------------------------------------------------- rendering

    def render_options(self, overrides: dict[str, Any] | None) -> RenderOptions:
        """Resolve render options for a photo/override on this frame."""
        return resolve(
            self.global_store.defaults,
            self.options.get(CONF_RENDER_DEFAULTS, {}),
            overrides,
        )

    def _key(self, source: str, overrides: dict[str, Any] | None) -> tuple[str, RenderOptions]:
        opts = self.render_options(overrides)
        canvas = self.canvas
        key = cache_key(source, opts.cache_dict(), asdict(canvas))
        return key, opts

    def _base_render(self, item: LibraryItem) -> tuple[str, Callable[[], RenderResult]]:
        """Cache key and producer of a library item's render without overlays.

        A photo is its original with its settings. A card is a solid fill, or the
        render of its background photo (the same cache entry that photo uses).
        """
        canvas = self.canvas
        if item.is_card:
            if (background := self.card_background_photo(item)) is not None:
                return self._base_render(background)
            color = item.background
            key = cache_key("fill:" + color, {}, asdict(canvas))
            return key, lambda: render_fill(color, canvas)
        key, opts = self._key(item.sha256, item.overrides)
        path = self.originals / item.filename
        return key, lambda: render(path.read_bytes(), opts, canvas)

    def card_background_photo(self, card: LibraryItem) -> LibraryItem | None:
        """The library photo a card is drawn on, if it has one."""
        if card.background != BACKGROUND_PHOTO:
            return None
        photo = self.get_photo(card.background_photo_id)
        return photo if photo is not None and not photo.is_card else None

    def photo_key(self, photo: LibraryItem) -> str:
        """Cache key of a library item's current render (without overlays)."""
        return self._base_render(photo)[0]

    async def _async_render_cached(self, key: str, produce: Callable[[], RenderResult]) -> str:
        if await self.hass.async_add_executor_job(self.cache.has, key):
            return key
        async with self._render_lock:
            if not await self.hass.async_add_executor_job(self.cache.has, key):
                result = await self.hass.async_add_executor_job(produce)
                await self.hass.async_add_executor_job(
                    self.cache.put, key, result.bmp, result.preview_png
                )
        return key

    async def async_render_photo(self, photo: LibraryItem) -> str:
        """Render a library item without overlays; return its cache key."""
        return await self._async_render_cached(*self._base_render(photo))

    def _override_base(self, ov: Override) -> tuple[str, Callable[[], RenderResult]]:
        """Cache key and producer of a one-off without overlays.

        A one-off text is a solid fill (the same cache entry a card with that
        background uses); its text is an overlay, see ``_text_overlay``.
        """
        canvas = self.canvas
        if ov.text is not None:
            color = ov.text["background"]
            key = cache_key("fill:" + color, {}, asdict(canvas))
            return key, lambda: render_fill(color, canvas)
        key, opts = self._key("override:" + ov.sha256, ov.overrides)
        path = self.directory / ov.filename
        return key, lambda: render(path.read_bytes(), opts, canvas)

    async def _async_render_override(self, ov: Override) -> str:
        return await self._async_render_cached(*self._override_base(ov))

    def placeholder_text(self) -> PlaceholderText:
        """What the "no photos yet" screen says, in HA's language."""
        german = (self.hass.config.language or "").startswith("de")
        return PlaceholderText(
            title=self.display_name,
            subtitle="Noch keine Fotos" if german else "No photos yet",
            hint=(
                "Fotos in Home Assistant unter „Bilderrahmen“ hinzufügen."
                if german
                else "Add photos in Home Assistant under Photo frames."
            ),
            footer=self.client_id,
        )

    def placeholder_key(self) -> str:
        """Cache key of the current "no photos yet" screen (changes with its text)."""
        return cache_key("placeholder", asdict(self.placeholder_text()), asdict(self.canvas))

    async def _async_render_placeholder(self) -> str:
        text = self.placeholder_text()
        canvas = self.canvas
        return await self._async_render_cached(
            self.placeholder_key(), lambda: render_placeholder(text, canvas)
        )

    async def async_preview(self, which: str) -> bytes | None:
        """Preview PNG of what is showing ("showing") or will show ("up_next")."""
        key = (
            self.state.served_key if which == "showing" else (await self._async_render_up_next())[1]
        )
        if key is None:
            return None
        return await self.hass.async_add_executor_job(self.cache.read_png, key)

    def _up_next_parts(self) -> tuple[str, LibraryItem | None, list[tuple[str, OverlayStyle]]]:
        """What the next wake shows: (kind, photo, overlays to draw with current values)."""
        kind, photo_id = self.up_next()
        photo = self.get_photo(photo_id) if kind == "photo" else None
        return kind, photo, self._draw_now(kind, photo)

    def _draw_now(self, kind: str, photo: LibraryItem | None) -> list[tuple[str, OverlayStyle]]:
        """Overlays drawn on a display, with the values they'd have right now."""
        applicable = self._applicable_overlays(kind, photo)
        variables = self.template_variables(photo)
        texts = {o.id: self.evaluate_overlay(o, variables)[0] for o in applicable}
        return self._overlay_draw_list(applicable, texts)

    async def _async_render_up_next(self) -> tuple[str, str]:
        """Render what the next wake shows; return (base key, key with overlays)."""
        kind, photo, draw = self._up_next_parts()
        if kind == "override" and self.state.override:
            base = await self._async_render_override(self.state.override)
        elif photo is not None:
            base = await self.async_render_photo(photo)
        else:
            base = await self._async_render_placeholder()
        # Up next shows overlays with the values they'd have right now.
        if draw:
            return base, await self._async_render_composite(base, draw)
        return base, base

    def _up_next_keys(self) -> tuple[str, str]:
        """Cache keys _async_render_up_next would use, without rendering."""
        kind, photo, draw = self._up_next_parts()
        if kind == "override" and self.state.override:
            base = self._override_base(self.state.override)[0]
        elif photo is not None:
            base = self.photo_key(photo)
        else:
            base = self.placeholder_key()
        return base, self._composite_key(base, draw) if draw else base

    async def async_photo_preview(self, photo_id: str) -> bytes | None:
        """Preview PNG of any library item; a card's has its overlays at their current values."""
        return await self._async_item_preview(self.require_photo(photo_id))

    async def _async_item_preview(self, item: LibraryItem) -> bytes | None:
        key = await self.async_render_photo(item)
        if item.is_card and (draw := self._draw_now("photo", item)):
            key = await self._async_render_composite(key, draw)
        return await self.hass.async_add_executor_job(self.cache.read_png, key)

    @callback
    def _schedule_prerender(self) -> None:
        if self._prerender_task and not self._prerender_task.done():
            self._prerender_task.cancel()
        self._prerender_task = self.entry.async_create_background_task(
            self.hass, self._async_prerender(), f"{DOMAIN} prerender {self.client_id}"
        )

    async def _async_prerender(self) -> None:
        await asyncio.sleep(1)
        try:
            await self._async_render_up_next()
        except Exception:
            _LOGGER.exception("Pre-rendering for %s failed", self.client_id)
        try:
            await self.async_housekeeping()
        except Exception:
            _LOGGER.exception("Cleaning up files for %s failed", self.client_id)

    async def async_housekeeping(self) -> None:
        """Delete files that are no longer needed.

        Needed are the image the frame shows, its base (to redraw overlays
        cheaply) and the next wake's base and image (with overlays at their
        current values). Everything else goes once unused for the grace period;
        see ``housekeeping`` for thumbs and others. Nothing is rendered here.
        """
        base, final = self._up_next_keys()
        st = self.state
        needed = {st.served_key, st.served_base_key, base, final}
        photos = {p.id: p.filename for p in self.photos if not p.is_card}
        override = {st.override.filename} if st.override and st.override.filename else set()
        await self.hass.async_add_executor_job(self._evict_files, needed, photos, override)

    def _evict_files(
        self, needed: set[str | None], photos: dict[str, str], override: set[str]
    ) -> None:
        deleted = self.cache.evict(needed)
        deleted += housekeeping.evict_thumbs(self.directory / "thumbs", photos.keys())
        deleted += housekeeping.evict_unreferenced(self.originals, "*", set(photos.values()))
        deleted += housekeeping.evict_unreferenced(self.directory, "override.*", override)
        if deleted:
            _LOGGER.debug("Deleted %d unneeded files for %s", deleted, self.client_id)

    def storage_usage(self) -> dict[str, dict[str, int]]:
        """File count and bytes of the render cache, thumbnails and originals. Blocking."""
        return {
            "cache": housekeeping.usage(self.cache.directory),
            "thumbs": housekeeping.usage(self.directory / "thumbs"),
            "originals": housekeeping.usage(self.originals),
        }

    # -------------------------------------------------------------- overlays

    @property
    def overlays(self) -> list[OverlayDef]:
        """Frame overlays, in drawing order."""
        return self.store.overlays

    def overlays_of(self, photo_id: str | None = None) -> list[OverlayDef]:
        """The overlay list of a photo, or the frame's (global) list without a photo."""
        return self.require_photo(photo_id).overlays if photo_id else self.overlays

    def _current_photo(self) -> LibraryItem | None:
        st = self.state
        return self.get_photo(st.current_id) if st.current_kind == "photo" else None

    def get_overlay(self, overlay_id: str, photo_id: str | None = None) -> OverlayDef | None:
        """Look up an overlay by id in a photo's list or the frame's."""
        return next((o for o in self.overlays_of(photo_id) if o.id == overlay_id), None)

    def require_overlay(self, overlay_id: str, photo_id: str | None = None) -> OverlayDef:
        """Look up an overlay or raise a validation error."""
        if (overlay := self.get_overlay(overlay_id, photo_id)) is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="overlay_not_found",
                translation_placeholders={"overlay_id": overlay_id},
            )
        return overlay

    def overlay_defs_hash(self, photo: LibraryItem | None = None) -> str:
        """Hash of the overlay definitions a display uses (edits invalidate evaluated texts)."""
        return _hash(
            {
                "photo": [o.as_dict() for o in photo.overlays] if photo else [],
                "global": [o.as_dict() for o in self.overlays],
            }
        )

    def _applicable_overlays(self, kind: str | None, photo: LibraryItem | None) -> list[OverlayDef]:
        """Enabled overlays drawn for a display, in drawing order.

        A photo's own overlays come first, global ones on top; the hide switch only
        removes the global ones. One-off images get global overlays only, a
        one-off text its text below them.
        """
        if kind not in ("photo", "override"):
            return []  # the placeholder stays as it is
        applicable: list[OverlayDef] = []
        if kind == "override" and (ov := self.state.override) is not None:
            if ov.text is not None:
                applicable.append(_text_overlay(ov))
            if not ov.overlays:
                return applicable
        if kind == "photo" and photo is not None:
            applicable += [o for o in photo.overlays if o.enabled]
        if photo is None or not photo.hide_frame_overlays:
            applicable += [o for o in self.overlays if o.enabled]
        return applicable

    def template_variables(self, photo: LibraryItem | None = None) -> dict[str, Any]:
        """Variables for overlay templates on this frame (``photo`` is None off the library)."""
        return template_variables(
            self.hass, self.display_name, photo_vars(photo) if photo is not None else None
        )

    def evaluate_overlay(
        self, overlay: OverlayDef, variables: dict[str, Any] | None = None
    ) -> tuple[str | None, str | None]:
        """Evaluate an overlay now: (text or None if hidden/empty, error or None)."""
        variables = variables if variables is not None else self.template_variables()
        try:
            if overlay.show_if and overlay.show_if.strip():
                shown = render_text(self.hass, overlay.show_if, variables)
                if not is_truthy(shown):
                    return None, None
            text = render_text(self.hass, overlay.template, variables).strip()
        except TemplateError as err:
            return None, str(err)
        return text or None, None

    @callback
    def _evaluate_overlays_for_wake(self) -> None:
        """Evaluate overlay texts once per wake, honouring each redraw policy."""
        st = self.state
        photo = self._current_photo()
        applicable = self._applicable_overlays(st.current_kind, photo)
        shown = (
            st.override.sha256 if st.current_kind == "override" and st.override else st.current_id
        )
        ident = f"{st.current_kind}:{shown}|{self.overlay_defs_hash(photo)}"
        same_display = ident == st.overlay_eval_base
        variables = self.template_variables(photo)
        texts: dict[str, str | None] = {}
        errors: dict[str, str] = {}
        for overlay in applicable:
            if same_display and overlay.redraw == "photo" and overlay.id in st.overlay_texts:
                texts[overlay.id] = st.overlay_texts[overlay.id]
                continue
            text, error = self.evaluate_overlay(overlay, variables)
            texts[overlay.id] = text
            if error:
                errors[overlay.id] = error
                _LOGGER.warning(
                    "Overlay %r on %s left out: %s", overlay.name, self.display_name, error
                )
        st.overlay_texts = texts
        st.overlay_errors = errors
        st.overlay_eval_base = ident

    @staticmethod
    def overlay_style(overlay: OverlayDef) -> OverlayStyle:
        """Drawing style of an overlay."""
        return OverlayStyle(
            anchor=overlay.anchor,
            margin=overlay.margin,
            width=overlay.width,
            align=overlay.align,
            size=overlay.size,
            text_color=overlay.text_color,
            backing=overlay.backing,
            backing_color=overlay.backing_color,
        )

    def _overlay_draw_list(
        self, overlays: list[OverlayDef], texts: dict[str, str | None]
    ) -> list[tuple[str, OverlayStyle]]:
        draw: list[tuple[str, OverlayStyle]] = []
        for overlay in overlays:
            text = texts.get(overlay.id)
            if text:
                draw.append((text, self.overlay_style(overlay)))
        return draw

    def _composite_key(self, base_key: str, draw: list[tuple[str, OverlayStyle]]) -> str:
        return cache_key(
            "composite:" + base_key,
            {"overlays": [(text, asdict(style)) for text, style in draw]},
            asdict(self.canvas),
        )

    async def _async_render_composite(
        self, base_key: str, draw: list[tuple[str, OverlayStyle]]
    ) -> str:
        canvas = self.canvas
        key = self._composite_key(base_key, draw)

        def produce() -> RenderResult:
            base = self.cache.read_bmp(base_key)
            if base is None:
                raise HomeAssistantError("Base image missing from cache")
            return composite(base, draw, canvas)

        return await self._async_render_cached(key, produce)

    async def async_overlay_preview(
        self,
        photo_id: str | None,
        overlays: list[OverlayDef] | None = None,
        for_photo: bool = False,
    ) -> tuple[bytes | None, dict[str, dict[str, str | None]]]:
        """Preview a photo with (draft) overlays evaluated now.

        ``overlays`` are drafts of the photo's own list (``for_photo``) or of the
        global list; the other list is drawn as stored (the global one not on a photo
        that hides it, unless it is the one being edited). Returns the PNG and, per
        overlay id, its evaluated text and error.
        """
        photo = self.get_photo(photo_id) if photo_id else None
        if for_photo and photo is None:
            self.require_photo(photo_id or "")
        if photo is None and self.photos:
            # Preview frame overlays on a photo rather than a card where there is one.
            photo = next((p for p in self.photos if not p.is_card), self.photos[0])
        own = (overlays if for_photo and overlays is not None else photo.overlays) if photo else []
        glob = self.overlays if for_photo or overlays is None else overlays
        hidden = for_photo and photo is not None and photo.hide_frame_overlays
        base = (
            await self.async_render_photo(photo)
            if photo
            else await self._async_render_placeholder()
        )
        variables = self.template_variables(photo)
        results: dict[str, dict[str, str | None]] = {}
        texts: dict[str, str | None] = {}
        for overlay in [*own, *glob]:
            text, error = (
                self.evaluate_overlay(overlay, variables) if overlay.enabled else (None, None)
            )
            results[overlay.id] = {"text": text, "error": error}
            texts[overlay.id] = text
        drawn = [o for o in own if o.enabled]
        if not hidden:
            drawn += [o for o in glob if o.enabled]
        key = base
        if draw := self._overlay_draw_list(drawn, texts):
            key = await self._async_render_composite(base, draw)
        png = await self.hass.async_add_executor_job(self.cache.read_png, key)
        return png, results

    @callback
    def async_save_overlay(self, overlay: OverlayDef, photo_id: str | None = None) -> OverlayDef:
        """Create or replace an overlay (matched by id) in a photo's list or the frame's."""
        target = self.overlays_of(photo_id)
        for index, existing in enumerate(target):
            if existing.id == overlay.id:
                target[index] = overlay
                break
        else:
            target.append(overlay)
        self._changed()
        return overlay

    @callback
    def async_delete_overlay(self, overlay_id: str, photo_id: str | None = None) -> None:
        """Remove an overlay."""
        overlay = self.require_overlay(overlay_id, photo_id)
        self.overlays_of(photo_id).remove(overlay)
        self._changed()

    @callback
    def async_reorder_overlays(self, order: list[str], photo_id: str | None = None) -> None:
        """Reorder overlays; ids not listed keep their relative order at the end."""
        target = self.overlays_of(photo_id)
        by_id = {o.id: o for o in target}
        ordered = [by_id[i] for i in dict.fromkeys(order) if i in by_id]
        rest = [o for o in target if o.id not in set(order)]
        target[:] = ordered + rest
        self._changed()

    @callback
    def async_copy_overlays_to(self, target: FrameManager, replace: bool = False) -> int:
        """Copy all overlays to another frame (new ids). Returns how many."""
        copies = copy_overlays(self.overlays)
        if replace:
            target.store.overlays[:] = copies
        else:
            target.store.overlays.extend(copies)
        target._changed()
        return len(copies)

    @callback
    def async_copy_photo_overlays(
        self, photo_id: str, to_photo_ids: list[str], replace: bool = False
    ) -> int:
        """Copy a photo's overlays to other photos of this frame (new ids). Returns how many."""
        source = self.require_photo(photo_id)
        targets = [self.require_photo(i) for i in dict.fromkeys(to_photo_ids) if i != photo_id]
        count = 0
        for target in targets:
            copies = copy_overlays(source.overlays)
            if replace:
                target.overlays[:] = copies
            else:
                target.overlays.extend(copies)
            count += len(copies)
        if targets:
            self._changed()
        return count

    @callback
    def async_set_photo_hide_overlays(self, photo_id: str, hide: bool) -> LibraryItem:
        """Whether frame overlays are drawn on a photo."""
        photo = self.require_photo(photo_id)
        photo.hide_frame_overlays = hide
        self._changed()
        return photo

    # --------------------------------------------------------------- library

    async def async_add_photo(
        self,
        data: bytes,
        name: str,
        overrides: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> LibraryItem:
        """Add image bytes to the library."""
        fmt = await self._async_validate(data)
        sha = hashlib.sha256(data).hexdigest()
        photo_id = secrets.token_hex(6)
        filename = f"{photo_id}.{_extension(fmt)}"
        await self.hass.async_add_executor_job((self.originals / filename).write_bytes, data)
        date, location = await self.hass.async_add_executor_job(
            read_capture, data, dt_util.get_default_time_zone()
        )
        photo = LibraryItem(
            id=photo_id,
            filename=filename,
            name=name or photo_id,
            sha256=sha,
            added=dt_util.utcnow().isoformat(),
            enabled=enabled,
            overrides=dict(overrides or {}),
            date=date,
            location=location,
            exif_read=True,
        )
        self.photos.append(photo)
        self._changed()
        return photo

    @callback
    def async_add_card(
        self,
        name: str | None,
        preset: str = "blank",
        background: str = "white",
        background_photo_id: str | None = None,
    ) -> LibraryItem:
        """Add a card made from a preset (texts in HA's language) to the library."""
        background, background_photo_id = self._card_background(background, background_photo_id)
        language = self.hass.config.language
        card = LibraryItem(
            id=secrets.token_hex(6),
            filename="",
            name=name or preset_name(preset, language),
            sha256="",
            added=dt_util.utcnow().isoformat(),
            kind=KIND_CARD,
            hide_frame_overlays=True,
            overlays=preset_overlays(preset, background, language),
            background=background,
            background_photo_id=background_photo_id,
        )
        self.photos.append(card)
        self._changed()
        return card

    def _card_background(
        self, background: str, background_photo_id: str | None
    ) -> tuple[str, str | None]:
        """Validate a card background; a photo background needs a photo of this frame."""
        if background != BACKGROUND_PHOTO:
            if background not in CARD_BACKGROUNDS:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="invalid_card_background"
                )
            return background, None
        photo = self.get_photo(background_photo_id)
        if photo is None or photo.is_card:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="invalid_card_background"
            )
        return background, photo.id

    async def _async_validate(self, data: bytes) -> str:
        if len(data) > MAX_UPLOAD_BYTES:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="image_too_large"
            )
        try:
            fmt, _, _ = await self.hass.async_add_executor_job(
                validate_image, data, MAX_IMAGE_PIXELS
            )
        except TooManyPixelsError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="image_too_many_pixels",
                translation_placeholders={
                    "megapixels": str(math.ceil(err.pixels / 1e6)),
                    "limit": str(MAX_IMAGE_PIXELS // 1_000_000),
                },
            ) from err
        except Exception as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_image",
                translation_placeholders={"error": str(err)},
            ) from err
        if fmt not in ALLOWED_FORMATS:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unsupported_format",
                translation_placeholders={"format": fmt},
            )
        return fmt

    async def async_remove_photo(self, photo_id: str) -> None:
        """Delete a photo from the library."""
        photo = self.require_photo(photo_id)
        self.photos.remove(photo)
        st = self.state
        if st.queued_id == photo_id:
            st.queued_id = None
        st.bag = [p for p in st.bag if p != photo_id]
        for card in self.cards_on(photo_id):
            card.background, card.background_photo_id = "white", None
        if not photo.is_card:
            await self.hass.async_add_executor_job(self._delete_photo_files, photo)
        self._changed()

    def cards_on(self, photo_id: str) -> list[LibraryItem]:
        """Cards that use a photo as their background."""
        return [
            p
            for p in self.photos
            if p.is_card and p.background == BACKGROUND_PHOTO and p.background_photo_id == photo_id
        ]

    def _delete_photo_files(self, photo: LibraryItem) -> None:
        (self.originals / photo.filename).unlink(missing_ok=True)
        for thumb in (self.directory / "thumbs").glob(f"{photo.id}_*.jpg"):
            thumb.unlink(missing_ok=True)

    @callback
    def async_update_photo(
        self,
        photo_id: str,
        *,
        name: str | None = None,
        enabled: bool | None = None,
        overrides: dict[str, Any] | None = None,
        reset: list[str] | None = None,
        background: str | None = None,
        background_photo_id: str | None = None,
    ) -> LibraryItem:
        """Change a photo's name, rotation membership or render overrides, or a card's background.

        A ``background_photo_id`` without ``background`` sets a photo background.
        """
        photo = self.require_photo(photo_id)
        if photo.is_card and (overrides or reset):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="card_has_no_render_settings"
            )
        if not photo.is_card and (background is not None or background_photo_id is not None):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="not_a_card",
                translation_placeholders={"photo_id": photo_id},
            )
        if background is not None or background_photo_id is not None:
            photo.background, photo.background_photo_id = self._card_background(
                background or BACKGROUND_PHOTO, background_photo_id or photo.background_photo_id
            )
        if name is not None:
            photo.name = name
        if enabled is not None:
            photo.enabled = enabled
        if reset:
            if "all" in reset:
                photo.overrides = {}
            for key in reset:
                photo.overrides.pop(key, None)
        if overrides:
            photo.overrides.update(overrides)
        self._changed()
        return photo

    @callback
    def async_move_photo(self, photo_id: str, position: int) -> None:
        """Move a photo to a position in the rotation order."""
        photo = self.require_photo(photo_id)
        self.photos.remove(photo)
        position = max(0, min(position, len(self.photos)))
        self.photos.insert(position, photo)
        self._changed()

    async def async_copy_photo_to(
        self, photo_id: str, target: FrameManager, enabled: bool | None = None
    ) -> LibraryItem:
        """Copy a library item into another frame's library.

        A photo takes its original, settings and overlays along. A card takes its
        overlays and background; a background photo is copied too (disabled), or
        the target's photo with the same content is used.
        """
        photo = self.require_photo(photo_id)
        enabled = photo.enabled if enabled is None else enabled
        if photo.is_card:
            return await self._async_copy_card_to(photo, target, enabled)
        data = await self.hass.async_add_executor_job((self.originals / photo.filename).read_bytes)
        copy = await target.async_add_photo(data, photo.name, dict(photo.overrides), enabled)
        if photo.overlays:
            copy.overlays[:] = copy_overlays(photo.overlays)
            target._changed()
        return copy

    async def _async_copy_card_to(
        self, card: LibraryItem, target: FrameManager, enabled: bool
    ) -> LibraryItem:
        background = "white" if card.background == BACKGROUND_PHOTO else card.background
        background_photo_id = None
        if (photo := self.card_background_photo(card)) is not None:
            same = next(
                (p for p in target.photos if not p.is_card and p.sha256 == photo.sha256), None
            )
            if same is None:
                same = await self.async_copy_photo_to(photo.id, target, enabled=False)
            background, background_photo_id = BACKGROUND_PHOTO, same.id
        copy = target.async_add_card(card.name, "blank", background, background_photo_id)
        copy.overlays[:] = copy_overlays(card.overlays)
        copy.hide_frame_overlays = card.hide_frame_overlays
        copy.enabled = enabled
        target._changed()
        return copy

    async def async_thumbnail(
        self, photo_id: str, size: int = 320, rotation: int = 0
    ) -> tuple[bytes, str]:
        """(image, content type) for a library item's thumbnail.

        A photo's is a JPEG of its original at a fixed size, optionally rotated
        (cached in ``thumbs/``). A card's is its preview PNG, evaluated now.
        """
        photo = self.require_photo(photo_id)
        if photo.is_card:
            return await self.async_photo_preview(photo_id) or b"", "image/png"
        if size not in THUMB_SIZES:
            size = THUMB_SIZES[0]
        rotation %= 360
        source = self.originals / photo.filename
        target = self.directory / "thumbs" / f"{photo.id}_{size}_{rotation}.jpg"
        jpeg = await self.hass.async_add_executor_job(
            make_thumbnail, source, target, size, rotation
        )
        return jpeg, "image/jpeg"

    async def async_render_preview(
        self,
        photo_id: str,
        overrides: dict[str, Any] | None,
        frame_defaults: dict[str, Any] | None = None,
        global_defaults: dict[str, Any] | None = None,
        background: tuple[str, str | None] | None = None,
        *,
        hide_frame_overlays: bool | None = None,
    ) -> bytes:
        """Preview PNG of a library item with unsaved settings (not cached).

        It is drawn with its overlays at their current values, like "Up next";
        ``hide_frame_overlays`` is an unsaved hide switch. A card is drawn on an
        unsaved ``background`` (background, background photo id) if given.
        """
        photo = self.require_photo(photo_id)
        if hide_frame_overlays is not None:
            photo = replace(photo, hide_frame_overlays=hide_frame_overlays)
        if photo.is_card:
            if background is not None:
                bg, bg_id = self._card_background(*background)
                photo = replace(photo, background=bg, background_photo_id=bg_id)
            return await self._async_item_preview(photo) or b""
        if global_defaults is None:
            global_defaults = self.global_store.defaults
        if frame_defaults is None:
            frame_defaults = self.options.get(CONF_RENDER_DEFAULTS, {})
        opts = resolve(
            global_defaults, frame_defaults, photo.overrides if overrides is None else overrides
        )
        path = self.originals / photo.filename
        canvas = self.canvas
        draw = self._draw_now("photo", photo)

        def produce() -> bytes:
            if not draw:
                return render_preview(path.read_bytes(), opts, canvas)
            return composite(render(path.read_bytes(), opts, canvas).bmp, draw, canvas).preview_png

        async with self._render_lock:
            return await self.hass.async_add_executor_job(produce)

    @callback
    def async_reorder(self, order: list[str]) -> None:
        """Reorder the library; ids not listed keep their relative order at the end."""
        by_id = {p.id: p for p in self.photos}
        ordered = [by_id[i] for i in dict.fromkeys(order) if i in by_id]
        rest = [p for p in self.photos if p.id not in set(order)]
        self.store.photos[:] = ordered + rest
        self._changed()

    @callback
    def async_set_overrides(self, photo_id: str, overrides: dict[str, Any]) -> LibraryItem:
        """Replace all render overrides of a photo."""
        photo = self.require_photo(photo_id)
        if photo.is_card and overrides:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="card_has_no_render_settings"
            )
        photo.overrides = dict(overrides)
        self._changed()
        return photo

    async def async_read_original(self, photo_id: str) -> bytes:
        """Return the original bytes of a photo."""
        photo = self.require_photo(photo_id)
        return await self.hass.async_add_executor_job((self.originals / photo.filename).read_bytes)

    # -------------------------------------------------------------- override

    async def async_set_override(
        self,
        data: bytes,
        name: str,
        overrides: dict[str, Any] | None,
        wakes: int | None,
        overlays: bool = True,
    ) -> None:
        """Show a one-off image instead of the rotation."""
        fmt = await self._async_validate(data)
        filename = f"override.{_extension(fmt)}"
        await self.hass.async_add_executor_job(self._replace_override_file, filename, data)
        self.state.override = Override(
            filename=filename,
            name=name,
            sha256=hashlib.sha256(data).hexdigest(),
            overrides=dict(overrides or {}),
            wakes_remaining=wakes,
            overlays=overlays,
        )
        self._changed()

    def _replace_override_file(self, filename: str, data: bytes) -> None:
        self._remove_override_files()
        (self.directory / filename).write_bytes(data)

    def _remove_override_files(self) -> None:
        for old in self.directory.glob("override.*"):
            old.unlink(missing_ok=True)

    async def async_set_text_override(
        self,
        text: dict[str, Any],
        name: str | None,
        wakes: int | None,
        overlays: bool = True,
    ) -> None:
        """Show a one-off text (template, background, size, anchor, align)."""
        await self.hass.async_add_executor_job(self._remove_override_files)
        self.state.override = Override(
            filename="",
            name=name or _text_name(text["template"]),
            sha256=_hash(text),
            wakes_remaining=wakes,
            overlays=overlays,
            text=dict(text),
        )
        self._changed()

    @callback
    def async_clear_override(self) -> None:
        """Return to the rotation on the next wake."""
        self.state.override = None
        self._changed()


def http_date(value: datetime) -> str:
    """Format an RFC 7231 HTTP date."""
    return value.astimezone(dt_util.UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")


TEXT_OVERLAY_ID = "show_text"


def _text_overlay(ov: Override) -> OverlayDef:
    """The single overlay a one-off text is drawn with, evaluated every wake."""
    assert ov.text is not None
    return OverlayDef(
        id=TEXT_OVERLAY_ID,
        name=ov.name,
        template=ov.text["template"],
        anchor=ov.text["anchor"],
        align=ov.text["align"],
        size=ov.text["size"],
        text_color=text_color_on(ov.text["background"]),
        backing="none",
        redraw="change",
    )


def _text_name(template: str) -> str:
    """A one-off text's name: its first line without markdown heading marks."""
    for line in template.splitlines():
        if line := line.strip().lstrip("#").strip():
            return line[:40]
    return "Text"


def _extension(fmt: str) -> str:
    return {"JPEG": "jpg", "MPO": "jpg", "PNG": "png", "WEBP": "webp", "HEIF": "heic"}.get(
        fmt, "img"
    )

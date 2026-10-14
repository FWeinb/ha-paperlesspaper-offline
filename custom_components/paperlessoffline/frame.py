"""Per-frame runtime: library, slideshow, rendering and request handling."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path
import secrets
import time
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from . import slideshow
from .cache import RenderCache, cache_key
from .const import (
    ALLOWED_FORMATS,
    CONF_AUTH_ENABLED,
    CONF_AUTH_PASSWORD,
    CONF_AUTH_USER,
    CONF_AUTO_ROTATION,
    CONF_CHARGER_MODE,
    CONF_CLIENT_ID,
    CONF_INTERVAL,
    CONF_MOTION_WAKEUP,
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
    EVENT_FRAME_WAKE,
    MAX_UPLOAD_BYTES,
    ORDER_SEQUENTIAL,
    PANELS,
    SETTINGS_GRACE_SECONDS,
    STORAGE_DIR,
    WAKE_DEBOUNCE_SECONDS,
    PanelSpec,
)
from .render import (
    Canvas,
    RenderOptions,
    RenderResult,
    canvas_for,
    make_thumbnail,
    render,
    render_placeholder,
    render_preview,
    validate_image,
)
from .schedule import parse_time, quiet_sleep
from .settings import resolve
from .store import FrameState, FrameStore, GlobalStore, Override, Photo

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

IMAGE_PATH = "/api/paperlessoffline/{token}/image.bmp"
SETTINGS_PATH = "/api/paperlessoffline/{token}/settings.json"
MAX_TELEMETRY_KEYS = 16


def signal_update(entry_id: str) -> str:
    """Dispatcher signal fired whenever a frame's state changes."""
    return f"{DOMAIN}_{entry_id}_update"


SIGNAL_ANY_UPDATE = f"{DOMAIN}_any_update"
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

    # ------------------------------------------------------------------ setup

    async def async_setup(self) -> None:
        """Load state and prepare directories."""
        await self.store.async_load()
        await self.hass.async_add_executor_job(self._make_dirs)

    def _make_dirs(self) -> None:
        self.originals.mkdir(parents=True, exist_ok=True)
        self.cache.directory.mkdir(parents=True, exist_ok=True)

    async def async_unload(self) -> None:
        """Flush state."""
        if self._prerender_task:
            self._prerender_task.cancel()
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
    def photos(self) -> list[Photo]:
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
        device = dr.async_get(self.hass).async_get_device_by_identifier(
            (DOMAIN, self.client_id), self.entry.entry_id
        )
        return device.id if device else None

    def image_path(self) -> str:
        """Path of the image endpoint."""
        return IMAGE_PATH.format(token=self.token)

    def settings_path(self) -> str:
        """Path of the settings endpoint."""
        return SETTINGS_PATH.format(token=self.token)

    def get_photo(self, photo_id: str | None) -> Photo | None:
        """Look up a photo by id."""
        return next((p for p in self.photos if p.id == photo_id), None)

    def require_photo(self, photo_id: str) -> Photo:
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
        self._changed()

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
        if is_wake:
            st.last_wake = now
            st.wake_count += 1
            self._advance()
            self._fire_wake()
        return is_wake

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

    async def async_handle_image_request(self, query: dict[str, str]) -> tuple[bytes, datetime]:
        """Return (bmp, last-modified) for the frame's image request."""
        async with self._lock:
            self._register_request(query, "image")
            key, name = await self._async_current_render()
            bmp = await self.hass.async_add_executor_job(self.cache.read_bmp, key)
            if bmp is None:
                raise HomeAssistantError("Rendered image disappeared")
            st = self.state
            if key != st.served_key:
                st.served_lm = max(int(time.time()), st.served_lm + 1)
                st.served_key = key
                st.served_name = name
            self._changed()
            return bmp, dt_util.utc_from_timestamp(st.served_lm)

    async def _async_current_render(self) -> tuple[str, str]:
        """Render (or fetch from cache) what should be on screen now."""
        st = self.state
        if st.current_kind == "override" and st.override is not None:
            return await self._async_render_override(st.override), st.override.name
        if st.current_kind == "photo":
            if photo := self.get_photo(st.current_id):
                return await self.async_render_photo(photo), photo.name
            if await self._async_served_available():
                # Deleted since the wake: keep what the frame already shows.
                return str(st.served_key), st.served_name or ""
            self._advance()
            if st.current_kind == "photo" and (photo := self.get_photo(st.current_id)):
                return await self.async_render_photo(photo), photo.name
        # Empty rotation: keep the last image, or show the placeholder.
        if await self._async_served_available():
            return str(st.served_key), st.served_name or ""
        return await self._async_render_placeholder(), "placeholder"

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

    async def async_handle_settings_request(
        self, query: dict[str, str], download_url: str, if_modified_since: str | None
    ) -> tuple[dict[str, Any] | None, datetime]:
        """Return (settings or None for 304, last-modified)."""
        async with self._lock:
            self._register_request(query, "settings")
            payload = self.effective_settings(download_url, dt_util.utcnow())
            st = self.state
            digest = _hash(payload)
            if digest != st.settings_hash:
                st.settings_hash = digest
                st.settings_lm = max(int(time.time()), st.settings_lm + 1)
            st.fetched_device_hash = self.device_settings_hash()
            st.last_settings_fetch = time.time()
            st.last_timeout = int(payload["timeout"])
            self._changed()
            last_modified = dt_util.utc_from_timestamp(st.settings_lm)
        if if_modified_since and if_modified_since.strip() == http_date(last_modified):
            return None, last_modified
        return payload, last_modified

    # ---------------------------------------------------------------- status

    def pending_changes(self) -> list[str]:
        """What the frame hasn't picked up yet."""
        pending = []
        if self.state.fetched_device_hash != self.device_settings_hash():
            pending.append("settings")
        if self.state.queued_id and self.get_photo(self.state.queued_id):
            pending.append("photo")
        ov = self.state.override
        if ov is not None and ov.shown == 0:
            pending.append("image")
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

    def photo_key(self, photo: Photo) -> str:
        """Cache key of a photo's current render."""
        return self._key(photo.sha256, photo.overrides)[0]

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

    async def async_render_photo(self, photo: Photo) -> str:
        """Render a library photo; return its cache key."""
        key, opts = self._key(photo.sha256, photo.overrides)
        path = self.originals / photo.filename
        canvas = self.canvas
        return await self._async_render_cached(key, lambda: render(path.read_bytes(), opts, canvas))

    async def _async_render_override(self, ov: Override) -> str:
        key, opts = self._key("override:" + ov.sha256, ov.overrides)
        path = self.directory / ov.filename
        canvas = self.canvas
        return await self._async_render_cached(key, lambda: render(path.read_bytes(), opts, canvas))

    async def _async_render_placeholder(self) -> str:
        title = self.entry.title
        canvas = self.canvas
        key = cache_key("placeholder:" + title, {}, asdict(canvas))
        return await self._async_render_cached(
            key,
            lambda: render_placeholder(
                title,
                ["No photos yet.", "Add photos in Home Assistant", f"ID: {self.client_id}"],
                canvas,
            ),
        )

    async def async_preview(self, which: str) -> bytes | None:
        """Preview PNG of what is showing ("showing") or will show ("up_next")."""
        if which == "showing":
            key = self.state.served_key
        else:
            kind, photo_id = self.up_next()
            if kind == "override" and self.state.override:
                key = await self._async_render_override(self.state.override)
            elif kind == "photo" and (photo := self.get_photo(photo_id)):
                key = await self.async_render_photo(photo)
            else:
                key = await self._async_render_placeholder()
        if key is None:
            return None
        return await self.hass.async_add_executor_job(self.cache.read_png, key)

    async def async_photo_preview(self, photo_id: str) -> bytes | None:
        """Preview PNG of any library photo."""
        photo = self.require_photo(photo_id)
        key = await self.async_render_photo(photo)
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
            await self.async_preview("up_next")
        except Exception:
            _LOGGER.exception("Pre-rendering for %s failed", self.client_id)
            return
        keep: list[str | None] = [self.state.served_key]
        kind, photo_id = self.up_next()
        if kind == "photo" and (photo := self.get_photo(photo_id)):
            keep.append(self.photo_key(photo))
        await self.hass.async_add_executor_job(self.cache.prune, keep)

    # --------------------------------------------------------------- library

    async def async_add_photo(
        self,
        data: bytes,
        name: str,
        overrides: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> Photo:
        """Add image bytes to the library."""
        fmt = await self._async_validate(data)
        sha = hashlib.sha256(data).hexdigest()
        photo_id = secrets.token_hex(6)
        filename = f"{photo_id}.{_extension(fmt)}"
        await self.hass.async_add_executor_job((self.originals / filename).write_bytes, data)
        photo = Photo(
            id=photo_id,
            filename=filename,
            name=name or photo_id,
            sha256=sha,
            added=dt_util.utcnow().isoformat(),
            enabled=enabled,
            overrides=dict(overrides or {}),
        )
        self.photos.append(photo)
        self._changed()
        return photo

    async def _async_validate(self, data: bytes) -> str:
        if len(data) > MAX_UPLOAD_BYTES:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="image_too_large"
            )
        try:
            fmt, _, _ = await self.hass.async_add_executor_job(validate_image, data)
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
        await self.hass.async_add_executor_job(self._delete_photo_files, photo)
        self._changed()

    def _delete_photo_files(self, photo: Photo) -> None:
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
    ) -> Photo:
        """Change a photo's name, rotation membership or render overrides."""
        photo = self.require_photo(photo_id)
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

    async def async_copy_photo_to(self, photo_id: str, target: FrameManager) -> Photo:
        """Copy a photo (original + overrides) into another frame's library."""
        photo = self.require_photo(photo_id)
        data = await self.hass.async_add_executor_job((self.originals / photo.filename).read_bytes)
        return await target.async_add_photo(data, photo.name, dict(photo.overrides), photo.enabled)

    async def async_thumbnail(self, photo_id: str, size: int = 320, rotation: int = 0) -> bytes:
        """JPEG of a photo's original at a fixed size, optionally rotated (cached)."""
        photo = self.require_photo(photo_id)
        if size not in THUMB_SIZES:
            size = THUMB_SIZES[0]
        rotation %= 360
        source = self.originals / photo.filename
        target = self.directory / "thumbs" / f"{photo.id}_{size}_{rotation}.jpg"
        return await self.hass.async_add_executor_job(
            make_thumbnail, source, target, size, rotation
        )

    async def async_render_preview(
        self,
        photo_id: str,
        overrides: dict[str, Any] | None,
        frame_defaults: dict[str, Any] | None = None,
        global_defaults: dict[str, Any] | None = None,
    ) -> bytes:
        """Preview PNG of a photo with unsaved settings (not cached)."""
        photo = self.require_photo(photo_id)
        if global_defaults is None:
            global_defaults = self.global_store.defaults
        if frame_defaults is None:
            frame_defaults = self.options.get(CONF_RENDER_DEFAULTS, {})
        opts = resolve(
            global_defaults, frame_defaults, photo.overrides if overrides is None else overrides
        )
        path = self.originals / photo.filename
        canvas = self.canvas
        async with self._render_lock:
            return await self.hass.async_add_executor_job(
                lambda: render_preview(path.read_bytes(), opts, canvas)
            )

    @callback
    def async_reorder(self, order: list[str]) -> None:
        """Reorder the library; ids not listed keep their relative order at the end."""
        by_id = {p.id: p for p in self.photos}
        ordered = [by_id[i] for i in dict.fromkeys(order) if i in by_id]
        rest = [p for p in self.photos if p.id not in set(order)]
        self.store.photos[:] = ordered + rest
        self._changed()

    @callback
    def async_set_overrides(self, photo_id: str, overrides: dict[str, Any]) -> Photo:
        """Replace all render overrides of a photo."""
        photo = self.require_photo(photo_id)
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
        )
        self._changed()

    def _replace_override_file(self, filename: str, data: bytes) -> None:
        for old in self.directory.glob("override.*"):
            old.unlink(missing_ok=True)
        (self.directory / filename).write_bytes(data)

    @callback
    def async_clear_override(self) -> None:
        """Return to the rotation on the next wake."""
        self.state.override = None
        self._changed()


def http_date(value: datetime) -> str:
    """Format an RFC 7231 HTTP date."""
    return value.astimezone(dt_util.UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")


def _extension(fmt: str) -> str:
    return {"JPEG": "jpg", "MPO": "jpg", "PNG": "png", "WEBP": "webp", "HEIF": "heic"}.get(
        fmt, "img"
    )

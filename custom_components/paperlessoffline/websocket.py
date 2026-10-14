"""Websocket API used by the sidebar panel."""

from __future__ import annotations

import base64
from datetime import timedelta
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.components.http.auth import async_sign_path
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util
import probatio as vol

from .const import (
    CONF_INTERVAL,
    CONF_MOUNTING,
    CONF_ORDER,
    CONF_RENDER_DEFAULTS,
    DOMAIN,
    GLOBAL_RENDER_DEFAULTS,
    MAX_INTERVAL,
    MIN_INTERVAL,
    ORDERS,
)
from .data import DATA_KEY, get_manager
from .frame import SIGNAL_ANY_UPDATE, FrameManager
from .issues import is_overdue
from .overlay_schema import OVERLAY_SCHEMA, build_overlay
from .render import MOUNTINGS
from .services import overlay_dict
from .settings import FRAME_DEFAULTS_SCHEMA, GLOBAL_DEFAULTS_SCHEMA, PHOTO_OVERRIDES_SCHEMA
from .sources import async_fetch_source
from .store import Photo

SIGN_EXPIRY = timedelta(hours=12)
SIGNAL_FRAMES_CHANGED = f"{DOMAIN}_frames_changed"


def _ts(value: float | None) -> str | None:
    return dt_util.utc_from_timestamp(value).isoformat() if value else None


def _jsonable(overrides: dict[str, Any]) -> dict[str, Any]:
    return {k: list(v) if isinstance(v, tuple) else v for k, v in overrides.items()}


def photo_info(hass: HomeAssistant, manager: FrameManager, photo: Photo) -> dict[str, Any]:
    """Serialise a photo for the panel, with signed image URLs."""
    entry_id = manager.entry.entry_id
    base = f"/api/{DOMAIN}/thumb/{entry_id}/{photo.id}.jpg"
    return {
        "photo_id": photo.id,
        "name": photo.name,
        "enabled": photo.enabled,
        "added": photo.added,
        "overrides": _jsonable(photo.overrides),
        "hide_frame_overlays": photo.hide_frame_overlays,
        "thumb_url": async_sign_path(hass, base, SIGN_EXPIRY),
        # The editor needs larger images; one per rotation so crops map 1:1.
        "display_urls": {
            str(rot): async_sign_path(hass, f"{base}?size=1280&rotation={rot}", SIGN_EXPIRY)
            for rot in (0, 90, 180, 270)
        },
    }


def frame_info(hass: HomeAssistant, manager: FrameManager) -> dict[str, Any]:
    """Serialise a frame's settings and status for the panel."""
    st = manager.state
    kind, next_id = manager.up_next()
    current = manager.get_photo(st.current_id) if st.current_kind == "photo" else None
    nxt = manager.get_photo(next_id)
    opts = manager.options
    return {
        "entry_id": manager.entry.entry_id,
        "title": manager.entry.title,
        "client_id": manager.client_id,
        "device_id": manager.device_id,
        "panel": {
            "model": manager.panel.model,
            "width": manager.panel.width,
            "height": manager.panel.height,
        },
        "canvas": {"width": manager.canvas.width, "height": manager.canvas.height},
        "mounting": opts.get(CONF_MOUNTING, manager.default_mounting),
        "order": manager.order,
        "interval": manager.interval,
        "render_defaults": _jsonable(opts.get(CONF_RENDER_DEFAULTS, {})),
        "last_seen": _ts(st.last_request),
        "last_wake": _ts(st.last_wake),
        "wake_count": st.wake_count,
        "pending": manager.pending_changes(),
        "current": {
            "kind": st.current_kind,
            "photo_id": current.id if current else None,
            "name": st.served_name,
        },
        "up_next": {"kind": kind, "photo_id": next_id, "name": nxt.name if nxt else None},
        "override": (
            {"name": st.override.name, "wakes_remaining": st.override.wakes_remaining}
            if st.override
            else None
        ),
        "photo_count": len(manager.photos),
        "enabled_count": len(manager.enabled_ids()),
        "ble": {**st.ble_status, "read_at": _ts(st.ble_read_at)},
        "overdue": is_overdue(manager),
        "needs_reprovision": manager.needs_reprovision(),
    }


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register websocket commands."""
    for handler in (
        ws_frames,
        ws_subscribe,
        ws_photos,
        ws_photo_update,
        ws_photo_delete,
        ws_photo_reorder,
        ws_photo_copy,
        ws_photo_show,
        ws_frame_skip,
        ws_frame_update,
        ws_import,
        ws_preview,
        ws_defaults,
        ws_defaults_set,
        ws_overlays,
        ws_overlay_save,
        ws_overlay_delete,
        ws_overlay_reorder,
        ws_overlays_copy,
        ws_overlay_preview,
    ):
        websocket_api.async_register_command(hass, handler)


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/frames"})
@callback
def ws_frames(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """List frames with status."""
    data = hass.data[DATA_KEY]
    frames = sorted(
        (frame_info(hass, m) for m in data.entries.values()), key=lambda f: f["title"].lower()
    )
    connection.send_result(msg["id"], {"frames": frames})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Notify the panel whenever a frame (or the set of frames) changes."""

    @callback
    def changed(entry_id: str | None = None) -> None:
        connection.send_message(websocket_api.event_message(msg["id"], {"entry_id": entry_id}))

    unsubs = [
        async_dispatcher_connect(hass, SIGNAL_ANY_UPDATE, changed),
        async_dispatcher_connect(hass, SIGNAL_FRAMES_CHANGED, changed),
    ]

    @callback
    def unsubscribe() -> None:
        for unsub in unsubs:
            unsub()

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])


_ENTRY: dict[Any, Any] = {vol.Required("entry_id"): cv.string}
_PHOTO: dict[Any, Any] = {**_ENTRY, vol.Required("photo_id"): cv.string}


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/photos", **_ENTRY})
@callback
def ws_photos(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """List a frame's photos."""
    manager = get_manager(hass, msg["entry_id"])
    connection.send_result(
        msg["id"], {"photos": [photo_info(hass, manager, p) for p in manager.photos]}
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/photo/update",
        **_PHOTO,
        vol.Optional("name"): cv.string,
        vol.Optional("enabled"): cv.boolean,
        vol.Optional("overrides"): PHOTO_OVERRIDES_SCHEMA,
        vol.Optional("hide_frame_overlays"): cv.boolean,
    }
)
@callback
def ws_photo_update(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Change a photo; ``overrides`` replaces all overrides."""
    manager = get_manager(hass, msg["entry_id"])
    photo = manager.async_update_photo(
        msg["photo_id"], name=msg.get("name"), enabled=msg.get("enabled")
    )
    if "overrides" in msg:
        photo = manager.async_set_overrides(msg["photo_id"], msg["overrides"])
    if "hide_frame_overlays" in msg:
        photo = manager.async_set_photo_hide_overlays(msg["photo_id"], msg["hide_frame_overlays"])
    connection.send_result(msg["id"], photo_info(hass, manager, photo))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/photo/delete", **_PHOTO})
@websocket_api.async_response
async def ws_photo_delete(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Delete a photo."""
    await get_manager(hass, msg["entry_id"]).async_remove_photo(msg["photo_id"])
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/photo/reorder",
        **_ENTRY,
        vol.Required("order"): [cv.string],
    }
)
@callback
def ws_photo_reorder(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Reorder the rotation."""
    get_manager(hass, msg["entry_id"]).async_reorder(msg["order"])
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/photo/copy",
        **_PHOTO,
        vol.Required("target_entry_id"): cv.string,
    }
)
@websocket_api.async_response
async def ws_photo_copy(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Copy a photo to another frame."""
    source = get_manager(hass, msg["entry_id"])
    target = get_manager(hass, msg["target_entry_id"])
    photo = await source.async_copy_photo_to(msg["photo_id"], target)
    connection.send_result(msg["id"], photo_info(hass, target, photo))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/photo/show", **_PHOTO})
@callback
def ws_photo_show(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Show a photo on the next wake."""
    get_manager(hass, msg["entry_id"]).async_queue_photo(msg["photo_id"])
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/frame/skip", **_ENTRY})
@callback
def ws_frame_skip(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Skip the photo that is up next."""
    get_manager(hass, msg["entry_id"]).async_skip()
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/frame/update",
        **_ENTRY,
        vol.Optional("order"): vol.In(ORDERS),
        vol.Optional("mounting"): vol.In(MOUNTINGS),
        vol.Optional("interval"): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_INTERVAL, max=MAX_INTERVAL)
        ),
        vol.Optional("render_defaults"): FRAME_DEFAULTS_SCHEMA,
    }
)
@callback
def ws_frame_update(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Change frame settings (stored in the config entry options)."""
    manager = get_manager(hass, msg["entry_id"])
    options = dict(manager.entry.options)
    for key, option in (
        ("order", CONF_ORDER),
        ("mounting", CONF_MOUNTING),
        ("interval", CONF_INTERVAL),
        ("render_defaults", CONF_RENDER_DEFAULTS),
    ):
        if key in msg:
            options[option] = _jsonable(msg[key]) if key == "render_defaults" else msg[key]
    hass.config_entries.async_update_entry(manager.entry, options=options)
    connection.send_result(msg["id"], frame_info(hass, manager))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/import",
        **_ENTRY,
        vol.Required("media_content_id"): cv.string,
    }
)
@websocket_api.async_response
async def ws_import(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Add a photo from a media source."""
    manager = get_manager(hass, msg["entry_id"])
    data, name = await async_fetch_source(hass, {"media_content_id": msg["media_content_id"]})
    photo = await manager.async_add_photo(data, name)
    connection.send_result(msg["id"], photo_info(hass, manager, photo))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/preview",
        **_PHOTO,
        vol.Optional("overrides"): PHOTO_OVERRIDES_SCHEMA,
        vol.Optional("frame_defaults"): FRAME_DEFAULTS_SCHEMA,
        vol.Optional("global_defaults"): GLOBAL_DEFAULTS_SCHEMA,
    }
)
@websocket_api.async_response
async def ws_preview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Render a dithered preview with (unsaved) settings."""
    manager = get_manager(hass, msg["entry_id"])
    png = await manager.async_render_preview(
        msg["photo_id"],
        msg.get("overrides"),
        msg.get("frame_defaults"),
        msg.get("global_defaults"),
    )
    connection.send_result(
        msg["id"],
        {
            "image": "data:image/png;base64," + base64.b64encode(png).decode(),
            "width": manager.canvas.width,
            "height": manager.canvas.height,
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/defaults"})
@callback
def ws_defaults(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return global render defaults and the built-in fallbacks."""
    connection.send_result(
        msg["id"],
        {
            "defaults": _jsonable(hass.data[DATA_KEY].global_store.defaults),
            "builtin": dict(GLOBAL_RENDER_DEFAULTS),
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/defaults/set",
        vol.Required("defaults"): GLOBAL_DEFAULTS_SCHEMA,
    }
)
@websocket_api.async_response
async def ws_defaults_set(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Replace the global render defaults."""
    data = hass.data[DATA_KEY]
    await data.global_store.async_set_defaults(_jsonable(msg["defaults"]))
    for manager in data.entries.values():
        manager.async_options_updated()
    connection.send_result(msg["id"], {"defaults": data.global_store.defaults})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/overlays", **_ENTRY})
@callback
def ws_overlays(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """List a frame's overlays with their last evaluated text and error."""
    manager = get_manager(hass, msg["entry_id"])
    connection.send_result(
        msg["id"], {"overlays": [overlay_dict(manager, o) for o in manager.overlays]}
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/overlay/save", **_ENTRY, vol.Required("overlay"): dict}
)
@callback
def ws_overlay_save(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Create (no id) or update (with id) an overlay."""
    manager = get_manager(hass, msg["entry_id"])
    data = OVERLAY_SCHEMA(msg["overlay"])
    existing = manager.get_overlay(data["id"]) if data.get("id") else None
    overlay = manager.async_save_overlay(build_overlay(data, existing))
    connection.send_result(msg["id"], overlay_dict(manager, overlay))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/overlay/delete", **_ENTRY, vol.Required("overlay_id"): str}
)
@callback
def ws_overlay_delete(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Delete an overlay."""
    get_manager(hass, msg["entry_id"]).async_delete_overlay(msg["overlay_id"])
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/overlay/reorder", **_ENTRY, vol.Required("order"): [str]}
)
@callback
def ws_overlay_reorder(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Reorder overlays (drawing order)."""
    get_manager(hass, msg["entry_id"]).async_reorder_overlays(msg["order"])
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/overlays/copy",
        **_ENTRY,
        vol.Required("target_entry_id"): str,
        vol.Optional("replace", default=False): bool,
    }
)
@callback
def ws_overlays_copy(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Copy all overlays to another frame."""
    source = get_manager(hass, msg["entry_id"])
    target = get_manager(hass, msg["target_entry_id"])
    connection.send_result(
        msg["id"], {"copied": source.async_copy_overlays_to(target, msg["replace"])}
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/overlay/preview",
        **_ENTRY,
        vol.Optional("photo_id"): vol.Any(None, str),
        vol.Optional("overlays"): [dict],
    }
)
@websocket_api.async_response
async def ws_overlay_preview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Render a photo with (draft) overlays evaluated now, plus each one's text or error."""
    manager = get_manager(hass, msg["entry_id"])
    drafts = None
    if "overlays" in msg:
        drafts = []
        for raw in msg["overlays"]:
            data = OVERLAY_SCHEMA(raw)
            existing = manager.get_overlay(data["id"]) if data.get("id") else None
            drafts.append(build_overlay(data, existing))
    png, results = await manager.async_overlay_preview(msg.get("photo_id"), drafts)
    connection.send_result(
        msg["id"],
        {
            "image": "data:image/png;base64," + base64.b64encode(png or b"").decode(),
            "width": manager.canvas.width,
            "height": manager.canvas.height,
            "results": results,
        },
    )

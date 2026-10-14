"""Actions for managing frame libraries and what frames show."""

from __future__ import annotations

from typing import Any

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.helpers import config_validation as cv
import probatio as vol

from .const import DOMAIN, RENDER_KEYS_FRAME_ONLY, RENDER_KEYS_PHOTO_ONLY, RENDER_KEYS_SHARED
from .data import DATA_KEY, get_manager
from .settings import FRAME_FIELDS, PHOTO_FIELDS
from .sources import ATTR_ENTITY, ATTR_FILE_PATH, ATTR_MEDIA, ATTR_URL, async_fetch_source

ATTR_ENTRY = "config_entry_id"
ATTR_TARGET_ENTRY = "target_config_entry_id"
ATTR_PHOTO = "photo_id"
ATTR_NAME = "name"
ATTR_ENABLED = "enabled"
ATTR_POSITION = "position"
ATTR_WAKES = "wakes"
ATTR_RESET = "reset"

SERVICE_ADD_PHOTO = "add_photo"
SERVICE_REMOVE_PHOTO = "remove_photo"
SERVICE_UPDATE_PHOTO = "update_photo"
SERVICE_MOVE_PHOTO = "move_photo"
SERVICE_COPY_PHOTO = "copy_photo"
SERVICE_SHOW_PHOTO = "show_photo"
SERVICE_NEXT_PHOTO = "next_photo"
SERVICE_SHOW_IMAGE = "show_image"
SERVICE_CLEAR_IMAGE = "clear_image"
SERVICE_LIST_PHOTOS = "list_photos"
SERVICE_SET_DEFAULTS = "set_defaults"

_ENTRY = {vol.Required(ATTR_ENTRY): cv.string}
_PHOTO = {**_ENTRY, vol.Required(ATTR_PHOTO): cv.string}
_SOURCE = {
    vol.Optional(ATTR_FILE_PATH): cv.string,
    vol.Optional(ATTR_URL): cv.string,
    vol.Optional(ATTR_MEDIA): vol.Any(cv.string, dict),
    vol.Optional(ATTR_ENTITY): cv.entity_domain(["camera", "image"]),
}
_PHOTO_OVERRIDES = {vol.Optional(k): v for k, v in PHOTO_FIELDS.items()}
_PHOTO_KEYS = RENDER_KEYS_SHARED + RENDER_KEYS_PHOTO_ONLY
_FRAME_KEYS = RENDER_KEYS_SHARED + RENDER_KEYS_FRAME_ONLY

SCHEMAS: dict[str, vol.Schema] = {
    SERVICE_ADD_PHOTO: vol.Schema(
        {
            **_ENTRY,
            **_SOURCE,
            vol.Optional(ATTR_NAME): cv.string,
            vol.Optional(ATTR_ENABLED, default=True): cv.boolean,
            **_PHOTO_OVERRIDES,
        }
    ),
    SERVICE_REMOVE_PHOTO: vol.Schema(_PHOTO),
    SERVICE_UPDATE_PHOTO: vol.Schema(
        {
            **_PHOTO,
            vol.Optional(ATTR_NAME): cv.string,
            vol.Optional(ATTR_ENABLED): cv.boolean,
            vol.Optional(ATTR_RESET): vol.All(cv.ensure_list, [vol.In((*_PHOTO_KEYS, "all"))]),
            **_PHOTO_OVERRIDES,
        }
    ),
    SERVICE_MOVE_PHOTO: vol.Schema(
        {**_PHOTO, vol.Required(ATTR_POSITION): vol.All(vol.Coerce(int), vol.Range(min=0))}
    ),
    SERVICE_COPY_PHOTO: vol.Schema({**_PHOTO, vol.Required(ATTR_TARGET_ENTRY): cv.string}),
    SERVICE_SHOW_PHOTO: vol.Schema(_PHOTO),
    SERVICE_NEXT_PHOTO: vol.Schema(_ENTRY),
    SERVICE_SHOW_IMAGE: vol.Schema(
        {
            **_ENTRY,
            **_SOURCE,
            vol.Optional(ATTR_NAME): cv.string,
            vol.Optional(ATTR_WAKES): vol.All(vol.Coerce(int), vol.Range(min=1)),
            **_PHOTO_OVERRIDES,
        }
    ),
    SERVICE_CLEAR_IMAGE: vol.Schema(_ENTRY),
    SERVICE_LIST_PHOTOS: vol.Schema(_ENTRY),
    SERVICE_SET_DEFAULTS: vol.Schema(
        {
            **{vol.Optional(k): v for k, v in FRAME_FIELDS.items()},
            vol.Optional(ATTR_RESET): vol.All(cv.ensure_list, [vol.In((*_FRAME_KEYS, "all"))]),
        }
    ),
}


def _overrides(call: ServiceCall, keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: call.data[k] for k in keys if k in call.data}


def _photo_dict(manager: Any, photo: Any) -> dict[str, Any]:
    return {
        "photo_id": photo.id,
        "name": photo.name,
        "enabled": photo.enabled,
        "added": photo.added,
        "overrides": {
            k: list(v) if isinstance(v, tuple) else v for k, v in photo.overrides.items()
        },
        "preview_url": f"/api/{DOMAIN}/preview/{manager.entry.entry_id}/{photo.id}.png",
    }


async def _add_photo(call: ServiceCall) -> ServiceResponse:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    data, name = await async_fetch_source(call.hass, dict(call.data))
    photo = await manager.async_add_photo(
        data,
        call.data.get(ATTR_NAME) or name,
        _overrides(call, _PHOTO_KEYS),
        call.data[ATTR_ENABLED],
    )
    return _photo_dict(manager, photo)


async def _remove_photo(call: ServiceCall) -> None:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    await manager.async_remove_photo(call.data[ATTR_PHOTO])


async def _update_photo(call: ServiceCall) -> ServiceResponse:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    photo = manager.async_update_photo(
        call.data[ATTR_PHOTO],
        name=call.data.get(ATTR_NAME),
        enabled=call.data.get(ATTR_ENABLED),
        overrides=_overrides(call, _PHOTO_KEYS),
        reset=call.data.get(ATTR_RESET),
    )
    return _photo_dict(manager, photo)


async def _move_photo(call: ServiceCall) -> None:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    manager.async_move_photo(call.data[ATTR_PHOTO], call.data[ATTR_POSITION])


async def _copy_photo(call: ServiceCall) -> ServiceResponse:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    target = get_manager(call.hass, call.data[ATTR_TARGET_ENTRY])
    photo = await manager.async_copy_photo_to(call.data[ATTR_PHOTO], target)
    return _photo_dict(target, photo)


async def _show_photo(call: ServiceCall) -> None:
    get_manager(call.hass, call.data[ATTR_ENTRY]).async_queue_photo(call.data[ATTR_PHOTO])


async def _next_photo(call: ServiceCall) -> None:
    get_manager(call.hass, call.data[ATTR_ENTRY]).async_skip()


async def _show_image(call: ServiceCall) -> None:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    data, name = await async_fetch_source(call.hass, dict(call.data))
    await manager.async_set_override(
        data,
        call.data.get(ATTR_NAME) or name,
        _overrides(call, _PHOTO_KEYS),
        call.data.get(ATTR_WAKES),
    )


async def _clear_image(call: ServiceCall) -> None:
    get_manager(call.hass, call.data[ATTR_ENTRY]).async_clear_override()


async def _list_photos(call: ServiceCall) -> ServiceResponse:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    kind, photo_id = manager.up_next()
    return {
        "photos": [_photo_dict(manager, p) for p in manager.photos],
        "current_photo_id": manager.state.current_id
        if manager.state.current_kind == "photo"
        else None,
        "up_next": {"kind": kind, "photo_id": photo_id},
    }


async def _set_defaults(call: ServiceCall) -> ServiceResponse:
    data = call.hass.data[DATA_KEY]
    defaults = dict(data.global_store.defaults)
    reset = call.data.get(ATTR_RESET) or []
    if "all" in reset:
        defaults = {}
    for key in reset:
        defaults.pop(key, None)
    defaults.update(_overrides(call, _FRAME_KEYS))
    await data.global_store.async_set_defaults(defaults)
    for manager in data.entries.values():
        manager.async_options_updated()
    return {"defaults": defaults}


HANDLERS: dict[str, tuple[Any, SupportsResponse]] = {
    SERVICE_ADD_PHOTO: (_add_photo, SupportsResponse.OPTIONAL),
    SERVICE_REMOVE_PHOTO: (_remove_photo, SupportsResponse.NONE),
    SERVICE_UPDATE_PHOTO: (_update_photo, SupportsResponse.OPTIONAL),
    SERVICE_MOVE_PHOTO: (_move_photo, SupportsResponse.NONE),
    SERVICE_COPY_PHOTO: (_copy_photo, SupportsResponse.OPTIONAL),
    SERVICE_SHOW_PHOTO: (_show_photo, SupportsResponse.NONE),
    SERVICE_NEXT_PHOTO: (_next_photo, SupportsResponse.NONE),
    SERVICE_SHOW_IMAGE: (_show_image, SupportsResponse.NONE),
    SERVICE_CLEAR_IMAGE: (_clear_image, SupportsResponse.NONE),
    SERVICE_LIST_PHOTOS: (_list_photos, SupportsResponse.ONLY),
    SERVICE_SET_DEFAULTS: (_set_defaults, SupportsResponse.OPTIONAL),
}


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration's actions."""
    for service, (handler, supports) in HANDLERS.items():
        hass.services.async_register(
            DOMAIN, service, handler, schema=SCHEMAS[service], supports_response=supports
        )

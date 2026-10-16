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
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
import probatio as vol

from .cards import CARD_BACKGROUNDS, PRESETS
from .const import DOMAIN, RENDER_KEYS_FRAME_ONLY, RENDER_KEYS_PHOTO_ONLY, RENDER_KEYS_SHARED
from .data import DATA_KEY, get_manager
from .overlay_schema import OVERLAY_FIELDS, build_overlay
from .render.pipeline import BACKGROUNDS
from .settings import FRAME_FIELDS, PHOTO_FIELDS
from .sources import ATTR_ENTITY, ATTR_FILE_PATH, ATTR_MEDIA, ATTR_URL, async_fetch_source
from .store import OverlayDef

ATTR_ENTRY = "config_entry_id"
ATTR_TARGET_ENTRY = "target_config_entry_id"
ATTR_PHOTO = "photo_id"
ATTR_TO_PHOTOS = "to_photo_ids"
ATTR_NAME = "name"
ATTR_ENABLED = "enabled"
ATTR_POSITION = "position"
ATTR_WAKES = "wakes"
ATTR_RESET = "reset"
ATTR_PRESET = "preset"
ATTR_BACKGROUND = "background"
ATTR_BACKGROUND_PHOTO = "background_photo_id"

SERVICE_ADD_PHOTO = "add_photo"
SERVICE_ADD_CARD = "add_card"
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
SERVICE_ADD_OVERLAY = "add_overlay"
SERVICE_UPDATE_OVERLAY = "update_overlay"
SERVICE_REMOVE_OVERLAY = "remove_overlay"
SERVICE_MOVE_OVERLAY = "move_overlay"
SERVICE_COPY_OVERLAYS = "copy_overlays"
SERVICE_LIST_OVERLAYS = "list_overlays"
ATTR_OVERLAY = "overlay_id"
ATTR_HIDE_OVERLAYS = "hide_frame_overlays"
ATTR_OVERLAYS = "overlays"
ATTR_REPLACE = "replace"

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

_OVERLAY_OPTIONAL = {vol.Optional(k): v for k, v in OVERLAY_FIELDS.items()}
_OVERLAY_ENTRY: dict[Any, Any] = {**_ENTRY, vol.Optional(ATTR_PHOTO): cv.string}
_OVERLAY_REF = {**_OVERLAY_ENTRY, vol.Required(ATTR_OVERLAY): cv.string}

SCHEMAS: dict[str, vol.Schema] = {
    SERVICE_ADD_OVERLAY: vol.Schema(
        {
            **_OVERLAY_ENTRY,
            vol.Required("name"): cv.string,
            vol.Required("template"): cv.string,
            **{k: v for k, v in _OVERLAY_OPTIONAL.items() if str(k) not in ("name", "template")},
        }
    ),
    SERVICE_UPDATE_OVERLAY: vol.Schema({**_OVERLAY_REF, **_OVERLAY_OPTIONAL}),
    SERVICE_REMOVE_OVERLAY: vol.Schema(_OVERLAY_REF),
    SERVICE_MOVE_OVERLAY: vol.Schema(
        {**_OVERLAY_REF, vol.Required(ATTR_POSITION): vol.All(vol.Coerce(int), vol.Range(min=0))}
    ),
    SERVICE_COPY_OVERLAYS: vol.Schema(
        {
            **_ENTRY,
            vol.Optional(ATTR_TARGET_ENTRY): cv.string,
            vol.Optional(ATTR_PHOTO): cv.string,
            vol.Optional(ATTR_TO_PHOTOS): vol.All(cv.ensure_list, [cv.string]),
            vol.Optional(ATTR_REPLACE, default=False): cv.boolean,
        }
    ),
    SERVICE_LIST_OVERLAYS: vol.Schema(_OVERLAY_ENTRY),
    SERVICE_ADD_PHOTO: vol.Schema(
        {
            **_ENTRY,
            **_SOURCE,
            vol.Optional(ATTR_NAME): cv.string,
            vol.Optional(ATTR_ENABLED, default=True): cv.boolean,
            **_PHOTO_OVERRIDES,
        }
    ),
    SERVICE_ADD_CARD: vol.Schema(
        {
            **_ENTRY,
            vol.Optional(ATTR_NAME): cv.string,
            vol.Optional(ATTR_PRESET, default="blank"): vol.In(PRESETS),
            vol.Optional(ATTR_BACKGROUND, default="white"): vol.In(CARD_BACKGROUNDS),
            vol.Optional(ATTR_BACKGROUND_PHOTO): cv.string,
        }
    ),
    SERVICE_REMOVE_PHOTO: vol.Schema(_PHOTO),
    SERVICE_UPDATE_PHOTO: vol.Schema(
        {
            **_PHOTO,
            vol.Optional(ATTR_NAME): cv.string,
            vol.Optional(ATTR_ENABLED): cv.boolean,
            vol.Optional(ATTR_HIDE_OVERLAYS): cv.boolean,
            vol.Optional(ATTR_RESET): vol.All(cv.ensure_list, [vol.In((*_PHOTO_KEYS, "all"))]),
            **_PHOTO_OVERRIDES,
            # A photo's render setting, or a card's background (checked per item).
            vol.Optional(ATTR_BACKGROUND): vol.In(CARD_BACKGROUNDS),
            vol.Optional(ATTR_BACKGROUND_PHOTO): cv.string,
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
            vol.Optional(ATTR_OVERLAYS, default=True): cv.boolean,
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
        "kind": photo.kind,
        "name": photo.name,
        "enabled": photo.enabled,
        "added": photo.added,
        "date": photo.date,
        "location": photo.location,
        "overrides": {
            k: list(v) if isinstance(v, tuple) else v for k, v in photo.overrides.items()
        },
        "hide_frame_overlays": photo.hide_frame_overlays,
        "overlay_count": len(photo.overlays),
        **card_fields(photo),
        "preview_url": f"/api/{DOMAIN}/preview/{manager.entry.entry_id}/{photo.id}.png",
    }


def card_fields(photo: Any) -> dict[str, Any]:
    """A card's background (empty for photos)."""
    if not photo.is_card:
        return {}
    return {"background": photo.background, "background_photo_id": photo.background_photo_id}


async def _add_card(call: ServiceCall) -> ServiceResponse:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    card = manager.async_add_card(
        call.data.get(ATTR_NAME),
        call.data[ATTR_PRESET],
        call.data[ATTR_BACKGROUND],
        call.data.get(ATTR_BACKGROUND_PHOTO),
    )
    return _photo_dict(manager, card)


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
    overrides = _overrides(call, _PHOTO_KEYS)
    background = None
    if manager.require_photo(call.data[ATTR_PHOTO]).is_card:
        background = overrides.pop(ATTR_BACKGROUND, None)
    elif overrides.get(ATTR_BACKGROUND, "white") not in BACKGROUNDS:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_a_card",
            translation_placeholders={"photo_id": call.data[ATTR_PHOTO]},
        )
    photo = manager.async_update_photo(
        call.data[ATTR_PHOTO],
        name=call.data.get(ATTR_NAME),
        enabled=call.data.get(ATTR_ENABLED),
        overrides=overrides,
        reset=call.data.get(ATTR_RESET),
        background=background,
        background_photo_id=call.data.get(ATTR_BACKGROUND_PHOTO),
    )
    if ATTR_HIDE_OVERLAYS in call.data:
        photo = manager.async_set_photo_hide_overlays(photo.id, call.data[ATTR_HIDE_OVERLAYS])
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
        call.data[ATTR_OVERLAYS],
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


def overlay_dict(manager: Any, overlay: OverlayDef) -> dict[str, Any]:
    """An overlay with the text and error from its last evaluation at a wake."""
    st = manager.state
    return {
        "overlay_id": overlay.id,
        **{k: v for k, v in overlay.as_dict().items() if k != "id"},
        "last_text": st.overlay_texts.get(overlay.id),
        "last_error": st.overlay_errors.get(overlay.id),
    }


async def _add_overlay(call: ServiceCall) -> ServiceResponse:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    overlay = manager.async_save_overlay(build_overlay(dict(call.data)), call.data.get(ATTR_PHOTO))
    return overlay_dict(manager, overlay)


async def _update_overlay(call: ServiceCall) -> ServiceResponse:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    photo_id = call.data.get(ATTR_PHOTO)
    existing = manager.require_overlay(call.data[ATTR_OVERLAY], photo_id)
    overlay = manager.async_save_overlay(build_overlay(dict(call.data), existing), photo_id)
    return overlay_dict(manager, overlay)


async def _remove_overlay(call: ServiceCall) -> None:
    get_manager(call.hass, call.data[ATTR_ENTRY]).async_delete_overlay(
        call.data[ATTR_OVERLAY], call.data.get(ATTR_PHOTO)
    )


async def _move_overlay(call: ServiceCall) -> None:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    photo_id = call.data.get(ATTR_PHOTO)
    overlay = manager.require_overlay(call.data[ATTR_OVERLAY], photo_id)
    order = [o.id for o in manager.overlays_of(photo_id) if o.id != overlay.id]
    order.insert(min(call.data[ATTR_POSITION], len(order)), overlay.id)
    manager.async_reorder_overlays(order, photo_id)


async def _copy_overlays(call: ServiceCall) -> ServiceResponse:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    if ATTR_PHOTO in call.data:
        if ATTR_TO_PHOTOS not in call.data:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="copy_overlays_needs_targets"
            )
        count = manager.async_copy_photo_overlays(
            call.data[ATTR_PHOTO], call.data[ATTR_TO_PHOTOS], call.data[ATTR_REPLACE]
        )
        return {"copied": count}
    if ATTR_TARGET_ENTRY not in call.data:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="copy_overlays_needs_targets"
        )
    target = get_manager(call.hass, call.data[ATTR_TARGET_ENTRY])
    count = manager.async_copy_overlays_to(target, call.data[ATTR_REPLACE])
    return {"copied": count}


async def _list_overlays(call: ServiceCall) -> ServiceResponse:
    manager = get_manager(call.hass, call.data[ATTR_ENTRY])
    overlays = manager.overlays_of(call.data.get(ATTR_PHOTO))
    return {"overlays": [overlay_dict(manager, o) for o in overlays]}


HANDLERS: dict[str, tuple[Any, SupportsResponse]] = {
    SERVICE_ADD_OVERLAY: (_add_overlay, SupportsResponse.OPTIONAL),
    SERVICE_UPDATE_OVERLAY: (_update_overlay, SupportsResponse.OPTIONAL),
    SERVICE_REMOVE_OVERLAY: (_remove_overlay, SupportsResponse.NONE),
    SERVICE_MOVE_OVERLAY: (_move_overlay, SupportsResponse.NONE),
    SERVICE_COPY_OVERLAYS: (_copy_overlays, SupportsResponse.OPTIONAL),
    SERVICE_LIST_OVERLAYS: (_list_overlays, SupportsResponse.ONLY),
    SERVICE_ADD_PHOTO: (_add_photo, SupportsResponse.OPTIONAL),
    SERVICE_ADD_CARD: (_add_card, SupportsResponse.OPTIONAL),
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
